"""异常/特例挖掘工具 — 数据故事 chatbot 用。

对 group_col 分组聚合 value_col 后，识别偏离整体分布的特例样本。
用于 EU 数据故事的「异常/例外案例」章节。

方法：
- iqr（默认）：Q3 + 1.5*IQR / Q1 - 1.5*IQR 之外为异常
- zscore：|z| > 2.5 为异常

降级路径：
- IQR=0（数据全相同或分布极度集中）→ fallback 到 zscore
- 都失败 → 返回 exceptions: [] + note
"""
import asyncio
import json
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from langchain.tools import tool

from app.agents.tools._charting_common import (
    _safe_read_df,
    save_fig_as_png,
)
from app.core.db import AsyncSessionLocal
from app.core.log import logger
from app.dao import data_download as download_dao


# 异常方向颜色
_SIDE_COLORS = {"high": "#e58c4f", "low": "#5b9bd5"}


# ───────── 异常检测 ─────────


def _detect_iqr(series: pd.Series) -> tuple[list[dict], float, float, float, str]:
    """IQR 方法，返回 (exceptions, lower, upper, iqr, note)。"""
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return [], 0.0, 0.0, 0.0, "IQR=0,fallback_to_zscore"

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    exceptions: list[dict] = []
    for g, v in series.items():
        if v > upper:
            deviations = (v - series.mean()) / (series.std() if series.std() > 0 else 1.0)
            exceptions.append({
                "group": str(g),
                "value": float(v),
                "side": "high",
                "deviation_score": round(float(deviations), 2),
                "boundary": float(upper),
            })
        elif v < lower:
            deviations = (v - series.mean()) / (series.std() if series.std() > 0 else 1.0)
            exceptions.append({
                "group": str(g),
                "value": float(v),
                "side": "low",
                "deviation_score": round(float(deviations), 2),
                "boundary": float(lower),
            })
    return exceptions, float(lower), float(upper), float(iqr), ""


def _detect_zscore(series: pd.Series, threshold: float = 2.5) -> tuple[list[dict], str]:
    """Z-score 方法，返回 (exceptions, note)。"""
    mean = float(series.mean())
    std = float(series.std())
    if std == 0:
        return [], "std=0,uniform_distribution"

    exceptions: list[dict] = []
    for g, v in series.items():
        z = (v - mean) / std
        if abs(z) > threshold:
            exceptions.append({
                "group": str(g),
                "value": float(v),
                "side": "high" if z > 0 else "low",
                "deviation_score": round(float(z), 2),
                "boundary": float(threshold),
            })
    return exceptions, ""


def _detect(series: pd.Series, method: str) -> dict[str, Any]:
    """对外统一入口：返回 {method, overall_mean, overall_std, exceptions, note}。"""
    overall_mean = float(series.mean()) if len(series) else 0.0
    overall_std = float(series.std()) if len(series) else 0.0

    if method == "iqr":
        exceptions, lower, upper, iqr, note = _detect_iqr(series)
        if note == "IQR=0,fallback_to_zscore":
            exceptions, note2 = _detect_zscore(series)
            return {
                "method": "zscore",
                "overall_mean": overall_mean,
                "overall_std": overall_std,
                "exceptions": exceptions,
                "note": note2 or note,
                "boundaries": {"lower": float(lower), "upper": float(upper), "iqr": float(iqr)},
            }
        return {
            "method": "iqr",
            "overall_mean": overall_mean,
            "overall_std": overall_std,
            "exceptions": exceptions,
            "note": note,
            "boundaries": {"lower": float(lower), "upper": float(upper), "iqr": float(iqr)},
        }

    # 默认 zscore
    exceptions, note = _detect_zscore(series)
    return {
        "method": "zscore",
        "overall_mean": overall_mean,
        "overall_std": overall_std,
        "exceptions": exceptions,
        "note": note,
        "boundaries": {},
    }


def _build_summary(detection: dict) -> str:
    """生成一句话总结。"""
    exceptions = detection["exceptions"]
    n = len(exceptions)
    if n == 0:
        return f"分布均匀({detection['method']}),未检测到显著异常(整体均值={detection['overall_mean']:.2f})"
    sides = {"high": 0, "low": 0}
    for e in exceptions:
        sides[e["side"]] += 1
    parts = [f"检测到 {n} 个偏离样本"]
    if sides["high"]:
        parts.append(f"{sides['high']} 个高于上边界")
    if sides["low"]:
        parts.append(f"{sides['low']} 个低于下边界")
    parts.append(f"整体均值={detection['overall_mean']:.2f},std={detection['overall_std']:.2f}")
    if detection.get("note"):
        parts.append(f"[{detection['note']}]")
    return "；".join(parts)


# ───────── 图表渲染 ─────────


def _render_exception_chart(
    exceptions: list[dict],
    overall_mean: float,
    chart_title: str,
    dataset_id: str,
) -> str | None:
    """水平条形图：每个异常样本一根条，颜色按 side 区分，叠加整体均值参考线。"""
    fig = None
    try:
        items = sorted(exceptions, key=lambda x: x["value"])
        labels = [e["group"][:14] for e in items]
        values = [e["value"] for e in items]
        colors = [_SIDE_COLORS[e["side"]] for e in items]

        fig, ax = plt.subplots(figsize=(9, max(3.5, 0.45 * len(items) + 2)))
        ax.barh(range(len(items)), values, color=colors, edgecolor="white")
        ax.axvline(overall_mean, color="#999", linestyle="--", linewidth=1.2, label=f"均值 {overall_mean:.2f}")
        ax.set_yticks(range(len(items)))
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_xlabel("value")
        ax.set_title(chart_title or "异常样本")

        from matplotlib.patches import Patch
        legend_patches = [
            Patch(facecolor=_SIDE_COLORS["high"], label="high (上偏)"),
            Patch(facecolor=_SIDE_COLORS["low"], label="low (下偏)"),
        ]
        ax.legend(handles=legend_patches, loc="lower right", fontsize=9)

        return save_fig_as_png(fig, dataset_id, "exception")
    except Exception as e:
        logger.warning("[exception_mining] chart render failed: {}", e)
        if fig:
            plt.close(fig)
        return None


# ───────── Tool 定义 ─────────


@tool
async def data_exception_mining(
    dataset_id: str,
    group_col: str,
    value_col: str,
    method: str = "iqr",
    top_k: int = 5,
    chart_title: str = "",
) -> str:
    """挖掘 group_col 分组后 value_col 偏离整体分布的特例样本。

    用于 EU 数据故事的「异常/例外案例」章节。

    Args:
        dataset_id: 数据集 ID
        group_col: 分组列名
        value_col: 聚合目标列（数值列）
        method: 异常检测方法，"iqr"（默认）或 "zscore"
        top_k: 最多返回的异常数（默认 5）
        chart_title: 图表标题（可选）

    Returns:
        JSON 字符串：
        {
            summary, method, overall_mean, overall_std,
            exceptions: [{group, value, side, deviation_score, boundary}, ...],
            chart_path, note, boundaries: {lower, upper, iqr}
        }
    """
    if not dataset_id or not group_col or not value_col:
        return json.dumps({
            "error": "dataset_id / group_col / value_col are required",
            "chart_path": None,
        }, ensure_ascii=False)

    method = (method or "iqr").lower()
    if method not in {"iqr", "zscore"}:
        method = "iqr"

    # 1. 拿数据文件
    try:
        async with AsyncSessionLocal() as session:
            dl_result = await download_dao.list_by_dataset(session, dataset_id, page=1, size=1)
            if not dl_result.get("ok") or not dl_result.get("items"):
                return json.dumps({
                    "error": f"数据集 {dataset_id[:12]}… 尚未上传数据文件",
                    "chart_path": None,
                }, ensure_ascii=False)
            file_path = dl_result["items"][0]["file_path"]
            file_format = dl_result["items"][0]["file_format"]
    except Exception as e:
        return json.dumps({"error": str(e), "chart_path": None}, ensure_ascii=False)

    # 2. 读 DataFrame
    try:
        df = await asyncio.to_thread(_safe_read_df, file_path, file_format)
    except Exception as e:
        return json.dumps({"error": f"读取失败: {e}", "chart_path": None}, ensure_ascii=False)

    if df.empty or group_col not in df.columns or value_col not in df.columns:
        return json.dumps({
            "error": f"列不存在或数据为空：group_col='{group_col}', value_col='{value_col}'",
            "chart_path": None,
        }, ensure_ascii=False)

    # 3. 分组聚合
    try:
        df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
        series = df.groupby(group_col)[value_col].mean().dropna()
    except Exception as e:
        return json.dumps({"error": f"分组聚合失败: {e}", "chart_path": None}, ensure_ascii=False)

    if series.empty:
        return json.dumps({
            "error": f"{value_col} 列无可用数值",
            "chart_path": None,
        }, ensure_ascii=False)

    # 4. 异常检测
    detection = _detect(series, method)

    # 限制返回数量（按 |deviation_score| 降序）
    exceptions_sorted = sorted(
        detection["exceptions"],
        key=lambda x: abs(x.get("deviation_score", 0)),
        reverse=True,
    )[:top_k]
    detection["exceptions"] = exceptions_sorted
    summary = _build_summary(detection)

    # 5. 渲染图表
    chart_path: str | None = None
    if exceptions_sorted:
        try:
            chart_path = await asyncio.to_thread(
                _render_exception_chart,
                exceptions_sorted,
                detection["overall_mean"],
                chart_title,
                dataset_id,
            )
        except Exception as e:
            logger.warning("[exception_mining] chart render error: {}", e)

    return json.dumps({
        "summary": summary,
        "method": detection["method"],
        "overall_mean": detection["overall_mean"],
        "overall_std": detection["overall_std"],
        "exceptions": detection["exceptions"],
        "chart_path": chart_path,
        "note": detection.get("note", ""),
        "boundaries": detection.get("boundaries", {}),
    }, ensure_ascii=False)


__all__ = ["data_exception_mining"]