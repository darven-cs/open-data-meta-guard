"""KMeans 聚类分层分析工具 — 数据故事 chatbot 用。

对数据按 group_col 分组聚合 value_col 后做 KMeans 聚类分层，
呈现「高/中/低梯度」对比，输出聚类标签、范围、样本数与水平条形图。

降级路径：
- n_clusters >= len(unique_groups) → 自动降级
- len(series) < n_clusters * 2 → 用 quantile binning 替代 KMeans
- 全部值相同 → 返回 note 而非抛异常
"""
import asyncio
import json
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from langchain.tools import tool
from sklearn.cluster import KMeans

from app.agents.tools._charting_common import (
    _safe_read_df,
    save_fig_as_png,
)
from app.core.db import AsyncSessionLocal
from app.core.log import logger
from app.dao import data_download as download_dao


# 聚类档位颜色（高→低）
_TIER_COLORS = ["#c41e3a", "#e58c4f", "#f0c674", "#5b9bd5", "#70ad47"]


# ───────── 聚类核心 ─────────


def _cluster_series(series: pd.Series, n_clusters: int) -> tuple[list[dict], dict[str, int]]:
    """对一组聚合值做 KMeans 聚类，返回 tiers 列表和 group→tier 映射。

    降级策略：
    1. len(series) < n_clusters * 2 → 改用 quantile binning
    2. n_clusters >= len(series) → 自动降级为 max(2, len(series) // 2)
    """
    items = [{"group": str(g), "value": float(v)} for g, v in series.items()]
    n = len(items)

    if n < 2:
        return (
            [{
                "label": "Tier_0_all",
                "range": [float(series.min()), float(series.max())],
                "count": n,
                "mean": float(series.mean()) if n else 0.0,
                "sum": float(series.sum()) if n else 0.0,
            }],
            {items[0]["group"]: 0} if items else {},
        )

    # 降级：样本过少无法稳定 KMeans → quantile binning
    actual_k = min(n_clusters, n)
    fallback = False
    if n < actual_k * 2:
        fallback = True
        actual_k = max(2, min(actual_k, n // 2))

    X = np.array([[v] for v in series.values], dtype=float)

    if fallback:
        # quantile binning fallback
        try:
            bins = np.quantile(X[:, 0], np.linspace(0, 1, actual_k + 1)[1:-1])
            labels = np.digitize(X[:, 0], bins)
        except Exception:
            labels = np.zeros(n, dtype=int)
    else:
        try:
            km = KMeans(n_clusters=actual_k, n_init=10, random_state=42)
            labels = km.fit_predict(X)
        except Exception as e:
            logger.warning("[cluster_analysis] KMeans failed, fallback to quantile: {}", e)
            bins = np.quantile(X[:, 0], np.linspace(0, 1, actual_k + 1)[1:-1])
            labels = np.digitize(X[:, 0], bins)

    # 把 cluster label 按均值从大到小排序 → "高/中/低"档位语义化
    cluster_means = {int(lab): float(series.values[labels == lab].mean()) for lab in set(labels)}
    sorted_labels = sorted(cluster_means.keys(), key=lambda x: cluster_means[x], reverse=True)
    rank = {lab: i for i, lab in enumerate(sorted_labels)}

    tier_groups: dict[int, list[str]] = {i: [] for i in range(len(sorted_labels))}
    for item, lab in zip(items, labels):
        tier_groups[rank[int(lab)]].append(item["group"])

    tiers: list[dict[str, Any]] = []
    for new_lab, orig_lab in enumerate(sorted_labels):
        mask = labels == orig_lab
        tier_values = series.values[mask]
        tiers.append({
            "label": f"Tier_{new_lab}",
            "range": [float(tier_values.min()), float(tier_values.max())],
            "count": int(mask.sum()),
            "mean": float(tier_values.mean()),
            "sum": float(tier_values.sum()),
        })

    group_to_tier = {item["group"]: rank[int(lab)] for item, lab in zip(items, labels)}

    if fallback:
        # 在 tiers 上挂个内部标记，调用方可读取
        for t in tiers:
            t["method_note"] = "quantile_binning_fallback"

    return tiers, group_to_tier


def _build_summary(tiers: list[dict], n: int, method_note: str = "") -> str:
    """生成聚类结果一句话总结。"""
    parts = [f"KMeans 聚类将 {n} 个样本分为 {len(tiers)} 档"]
    for t in tiers:
        parts.append(
            f"{t['label']}(n={t['count']}, mean={t['mean']:.2f}, range=[{t['range'][0]:.2f}, {t['range'][1]:.2f}])"
        )
    if method_note:
        parts.append(f"[{method_note}]")
    return "；".join(parts)


# ───────── 图表渲染 ─────────


def _render_cluster_chart(
    items: list[dict],
    group_to_tier: dict[str, int],
    tiers: list[dict],
    chart_title: str,
    dataset_id: str,
) -> str | None:
    """水平条形图：y 轴 group 名（按档着色），x 轴 value。"""
    fig = None
    try:
        # 按 tier 排序输出：高档在上
        sorted_items = sorted(
            items, key=lambda x: (group_to_tier.get(x["group"], 0), -x["value"])
        )
        labels = [it["group"][:14] for it in sorted_items]
        values = [it["value"] for it in sorted_items]
        colors = [_TIER_COLORS[group_to_tier[it["group"]] % len(_TIER_COLORS)] for it in sorted_items]

        height = max(4.0, min(14.0, 0.32 * len(items) + 2.5))
        fig, ax = plt.subplots(figsize=(10, height))
        ax.barh(range(len(sorted_items)), values, color=colors, edgecolor="white")
        ax.set_yticks(range(len(sorted_items)))
        ax.set_yticklabels(labels)
        ax.invert_yaxis()  # 高值在顶部
        ax.set_xlabel("value")
        ax.set_title(chart_title or f"KMeans cluster (k={len(tiers)})")

        # 图例
        from matplotlib.patches import Patch
        legend_patches = [
            Patch(facecolor=_TIER_COLORS[i % len(_TIER_COLORS)], label=tiers[i]["label"])
            for i in range(len(tiers))
        ]
        ax.legend(handles=legend_patches, loc="lower right", fontsize=9)

        return save_fig_as_png(fig, dataset_id, "cluster")
    except Exception as e:
        logger.warning("[cluster_analysis] chart render failed: {}", e)
        if fig:
            plt.close(fig)
        return None


# ───────── Tool 定义 ─────────


@tool
async def data_cluster_analysis(
    dataset_id: str,
    group_col: str,
    value_col: str,
    n_clusters: int = 3,
    top_n: int = 15,
    chart_title: str = "",
) -> str:
    """对数据按 group_col 分组聚合 value_col 后做 KMeans 聚类分层。

    用于 EU 数据故事的「聚类分组分析」章节：呈现高/中/低梯度对比。

    Args:
        dataset_id: 数据集 ID（来自 kg_query 返回的 dataset_id）
        group_col: 分组列名（如「地区」「年份」「类别」）
        value_col: 聚合目标列名（数值列）
        n_clusters: 聚类档位数（默认 3，过少样本会自动降级）
        top_n: 图表最多显示的样本数（默认 15）
        chart_title: 图表标题（可选）

    Returns:
        JSON 字符串：
        {
            summary, method, n_clusters,
            tiers: [{label, range, count, mean, sum}, ...],
            items_by_tier: {Tier_0: [{group, value}, ...], ...},
            chart_path: "charts/<dataset_id>/cluster_<ts>.png",
            limitations: [...]
        }
    """
    if not dataset_id or not group_col or not value_col:
        return json.dumps({
            "error": "dataset_id / group_col / value_col are required",
            "chart_path": None,
        }, ensure_ascii=False)

    if n_clusters < 2:
        n_clusters = 2
    if n_clusters > 10:
        n_clusters = 10

    # 1. 拿数据文件路径
    try:
        async with AsyncSessionLocal() as session:
            dl_result = await download_dao.list_by_dataset(session, dataset_id, page=1, size=1)
            if not dl_result.get("ok") or not dl_result.get("items"):
                return json.dumps({
                    "error": f"数据集 {dataset_id[:12]}… 尚未上传数据文件，无法分析",
                    "chart_path": None,
                }, ensure_ascii=False)
            file_path = dl_result["items"][0]["file_path"]
            file_format = dl_result["items"][0]["file_format"]
    except Exception as e:
        logger.error("[cluster_analysis] DB query failed: {}", e)
        return json.dumps({"error": str(e), "chart_path": None}, ensure_ascii=False)

    # 2. 读 DataFrame
    try:
        df = await asyncio.to_thread(_safe_read_df, file_path, file_format)
    except Exception as e:
        logger.error("[cluster_analysis] read failed: {}", e)
        return json.dumps({"error": f"读取失败: {e}", "chart_path": None}, ensure_ascii=False)

    if df.empty or group_col not in df.columns or value_col not in df.columns:
        return json.dumps({
            "error": f"列不存在或数据为空：group_col='{group_col}', value_col='{value_col}'",
            "chart_path": None,
        }, ensure_ascii=False)

    # 3. 分组聚合
    try:
        # 强制数值化（非数值会被置 NaN）
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        series = df.groupby(group_col)[value_col].mean().dropna().sort_values(ascending=False)
    except Exception as e:
        return json.dumps({
            "error": f"分组聚合失败: {e}",
            "chart_path": None,
        }, ensure_ascii=False)

    if series.empty:
        return json.dumps({
            "error": f"{value_col} 列无可用数值",
            "chart_path": None,
        }, ensure_ascii=False)

    # 4. 聚类
    items = [{"group": str(g), "value": float(v)} for g, v in series.items()]
    tiers, group_to_tier = _cluster_series(series, n_clusters)

    # 5. 按 tier 聚合 items
    items_by_tier: dict[str, list[dict]] = {}
    for t in tiers:
        items_by_tier[t["label"]] = []
    for it in items:
        tier_idx = group_to_tier.get(it["group"], 0)
        tier_label = f"Tier_{tier_idx}"
        if tier_label in items_by_tier and len(items_by_tier[tier_label]) < top_n:
            items_by_tier[tier_label].append(it)

    method_note = next((t.get("method_note") for t in tiers if t.get("method_note")), "")
    method = "quantile_binning" if method_note else "KMeans"
    summary = _build_summary(tiers, len(items), method_note)

    # 6. 渲染图表（线程池）
    chart_path: str | None = None
    try:
        chart_path = await asyncio.to_thread(
            _render_cluster_chart,
            items[: max(top_n, len(items))],
            group_to_tier,
            tiers,
            chart_title,
            dataset_id,
        )
    except Exception as e:
        logger.warning("[cluster_analysis] chart render error: {}", e)

    return json.dumps({
        "summary": summary,
        "method": method,
        "n_clusters": len(tiers),
        "tiers": tiers,
        "items_by_tier": items_by_tier,
        "chart_path": chart_path,
        "limitations": [
            "n_clusters 由 LLM 指定;样本数过少时自动降级为 quantile binning",
            "聚类仅基于 group_col 聚合后的均值,未考虑原始分布形状",
        ],
    }, ensure_ascii=False)


__all__ = ["data_cluster_analysis"]