"""数据分析与图表生成工具 — 数据故事 chatbot 用。

设计要点：
- **不用 exec()，用参数化分析函数**：LLM 选分析类型 + 传参数，
  工具内部调用对应 pandas/matplotlib 方法，安全可控。
- **matplotlib Agg backend + asyncio.to_thread()**：无显示器 + 不阻塞事件循环。
- **中文支持**：自动尝试多个中文字体。

支持的分析类型：
- describe / value_counts / groupby / corr_matrix / null_analysis
- histogram / bar_chart / line_chart / scatter / pie_chart
"""
import asyncio
import io
import json
import os
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 必须在 import pyplot 之前设置

import matplotlib.pyplot as plt
import pandas as pd
from langchain.tools import tool

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.log import logger
from app.dao import data_download as download_dao
from app.model.data_download import DataDownload


# ───────── 中文支持 ─────────

# 按优先级尝试中文字体
_CN_FONT_CANDIDATES = [
    "Noto Sans CJK SC",
    "SimHei",
    "WenQuanYi Micro Hei",
    "WenQuanYi Zen Hei",
    "Noto Sans SC",
    "AR PL UMing CN",
    "DejaVu Sans",
]
_CN_FONT = None

for _f in _CN_FONT_CANDIDATES:
    try:
        from matplotlib.font_manager import FontProperties
        FontProperties(family=_f)
        _CN_FONT = _f
        break
    except Exception:
        continue

if _CN_FONT:
    plt.rcParams["font.sans-serif"] = [_CN_FONT, "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    logger.info("[data_analysis_tool] using font: {}", _CN_FONT)
else:
    logger.warning("[data_analysis_tool] no CJK font found, chart labels may render as tofu")


# ───────── 图表目录 ─────────

def _charts_dir() -> Path:
    base = Path(settings.download_dir).resolve()
    return base / "charts"


_CHARTS_DIR = _charts_dir()


# ───────── 分析类型常量 ─────────

ANALYSIS_TYPES = [
    "describe",
    "value_counts",
    "groupby",
    "corr_matrix",
    "null_analysis",
    "histogram",
    "bar_chart",
    "line_chart",
    "scatter",
    "pie_chart",
]


# ───────── 守护函数 ─────────

def _safe_read_df(file_path: str, file_format: str) -> pd.DataFrame:
    """安全读取 CSV/XLSX，返回 DataFrame。"""
    fmt = file_format.lower()
    if fmt == "csv":
        return pd.read_csv(file_path, nrows=settings.quality_sample_size)
    elif fmt in ("xls", "xlsx"):
        return pd.read_excel(file_path, nrows=settings.quality_sample_size)
    elif fmt == "json":
        return pd.read_json(file_path)
    else:
        raise ValueError(f"unsupported file format: {fmt}")


# ───────── 分析函数 ─────────


def _analysis_describe(df: pd.DataFrame, **_kwargs) -> dict:
    """汇总统计。"""
    desc = df.describe(include="all").to_dict()
    return {"summary": str(df.describe(include="all")), "stats": desc}


def _analysis_value_counts(df: pd.DataFrame, columns: list[str] | None = None, **_kwargs) -> dict:
    """指定列的频次分布。"""
    cols = columns or df.columns.tolist()
    result = {}
    for col in cols[:5]:  # 最多 5 列，防止输出爆炸
        if col in df.columns:
            vc = df[col].value_counts().head(20).to_dict()
            # key 可能是数字/时间等，转 str
            result[col] = {str(k): v for k, v in vc.items()}
    return {"summary": json.dumps(result, ensure_ascii=False, default=str), "stats": result}


def _analysis_groupby(
    df: pd.DataFrame,
    group_col: str | None = None,
    agg_col: str | None = None,
    agg_func: str = "mean",
    **_kwargs,
) -> dict:
    """按某列分组聚合。"""
    if not group_col or group_col not in df.columns:
        return {"summary": f"错误: group_col '{group_col}' 不存在", "stats": {}}
    if not agg_col or agg_col not in df.columns:
        return {"summary": f"错误: agg_col '{agg_col}' 不存在", "stats": {}}

    try:
        grouped = df.groupby(group_col)[agg_col].agg(agg_func).sort_values(ascending=False).head(30)
        result = {str(k): v for k, v in grouped.to_dict().items()}
        return {"summary": json.dumps(result, ensure_ascii=False, default=str), "stats": result}
    except Exception as e:
        return {"summary": f"groupby 失败: {e}", "stats": {}}


def _analysis_corr(df: pd.DataFrame, **_kwargs) -> dict:
    """数值列相关性矩阵。"""
    num_df = df.select_dtypes(include=["number"])
    if num_df.empty:
        return {"summary": "无数值列，无法计算相关性矩阵", "stats": {}}
    corr = num_df.corr().to_dict()
    return {"summary": str(num_df.corr()), "stats": corr}


def _analysis_nulls(df: pd.DataFrame, **_kwargs) -> dict:
    """缺失值分析。"""
    nulls = df.isnull().sum()
    null_pct = (df.isnull().sum() / len(df) * 100).round(2)
    result = {}
    for col in df.columns:
        if nulls[col] > 0:
            result[col] = {"count": int(nulls[col]), "pct": float(null_pct[col])}
    return {
        "summary": f"缺失列数: {len(result)}, 总缺失率: {df.isnull().sum().sum() / df.size * 100:.2f}%",
        "stats": result,
    }


# ───────── 图表渲染函数（在 executor 线程中运行）─────────


def _render_chart(
    df: pd.DataFrame,
    analysis_type: str,
    columns: list[str] | None = None,
    group_col: str | None = None,
    agg_col: str | None = None,
    agg_func: str = "mean",
    bins: int = 10,
    chart_title: str = "",
    output_dir: str = "",
) -> str | None:
    """在后台线程中渲染 matplotlib 图表并保存为 PNG。

    Returns:
        生成的图表文件路径（相对 charts/..），或 None 表示不生成图表。
    """
    cols = columns or []
    fig = None

    try:
        if analysis_type == "histogram":
            col = cols[0] if cols else df.select_dtypes(include=["number"]).columns[0]
            fig, ax = plt.subplots(figsize=(8, 5))
            ax.hist(df[col].dropna(), bins=bins, edgecolor="white", color="#c41e3a")
            ax.set_xlabel(col)
            ax.set_ylabel("频次")
            ax.set_title(chart_title or f"{col} 分布直方图")

        elif analysis_type == "bar_chart":
            x_col = cols[0] if cols else df.columns[0]
            y_col = cols[1] if len(cols) > 1 else df.select_dtypes(include=["number"]).columns[0]
            top = df.groupby(x_col)[y_col].mean().sort_values(ascending=False).head(15)
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.bar(range(len(top)), top.values, color="#c41e3a")
            ax.set_xticks(range(len(top)))
            ax.set_xticklabels([str(l)[:12] for l in top.index], rotation=45, ha="right")
            ax.set_ylabel(y_col)
            ax.set_title(chart_title or f"{x_col} → {y_col} 柱状图")

        elif analysis_type == "line_chart":
            x_col = cols[0] if cols else df.columns[0]
            y_col = cols[1] if len(cols) > 1 else df.select_dtypes(include=["number"]).columns[0]
            top = df.groupby(x_col)[y_col].mean().sort_index().head(30)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(range(len(top)), top.values, color="#c41e3a", marker="o", markersize=3)
            ax.set_xticks(range(len(top)))
            ax.set_xticklabels([str(l)[:12] for l in top.index], rotation=45, ha="right")
            ax.set_ylabel(y_col)
            ax.set_title(chart_title or f"{x_col} → {y_col} 折线图")

        elif analysis_type == "scatter":
            x_col = cols[0] if cols else df.select_dtypes(include=["number"]).columns[0]
            y_col = cols[1] if len(cols) > 1 else df.select_dtypes(include=["number"]).columns[-1]
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.scatter(df[x_col], df[y_col], alpha=0.5, color="#c41e3a", s=10)
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            ax.set_title(chart_title or f"{x_col} vs {y_col} 散点图")

        elif analysis_type == "pie_chart":
            col = cols[0] if cols else df.columns[0]
            top = df[col].value_counts().head(10)
            fig, ax = plt.subplots(figsize=(8, 8))
            ax.pie(top.values, labels=[str(l)[:15] for l in top.index], autopct="%1.1f%%")
            ax.set_title(chart_title or f"{col} 饼图")

        else:
            return None  # describe/value_counts/groupby/corr/null_analysis 不生成图表

        # 保存 PNG
        dataset_dir = Path(output_dir)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time() * 1000)
        filename = f"{analysis_type}_{timestamp}.png"
        filepath = dataset_dir / filename
        fig.savefig(filepath, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)

        # 返回相对路径
        rel_path = filepath.relative_to(_CHARTS_DIR.parent)
        return str(rel_path)

    except Exception as e:
        logger.warning("[data_analysis_tool] chart render failed for {}: {}", analysis_type, e)
        if fig:
            plt.close(fig)
        return None


# ───────── Tool 定义 ─────────


@tool
async def analyze_and_chart(
    dataset_id: str,
    analysis_type: str,
    columns: list[str] | None = None,
    group_col: str | None = None,
    agg_col: str | None = None,
    agg_func: str = "mean",
    bins: int = 10,
    chart_title: str = "",
) -> str:
    """对指定数据集进行统计分析并可选生成图表（PNG）。

    内部流程:
    1. 查 DataDownload 表获取数据文件路径
    2. pandas 读 CSV/XLSX
    3. 根据 analysis_type 调用对应分析函数
    4. matplotlib (Agg backend) 生成图表到 data/charts/{dataset_id}/{timestamp}.png
    5. 返回 JSON: {summary, chart_path, stats}

    Args:
        dataset_id: 数据集 ID（来自 kg_query 返回的 dataset_id）
        analysis_type: 分析类型，可选: describe, value_counts, groupby, corr_matrix,
                       null_analysis, histogram, bar_chart, line_chart, scatter, pie_chart
        columns: 分析的列名列表（value_counts/histogram 等需要指定）
        group_col: groupby 时的分组列
        agg_col: groupby 时的聚合目标列
        agg_func: 聚合函数，默认 "mean"（支持 mean/sum/count/min/max/std）
        bins: 直方图分箱数，默认 10
        chart_title: 图表标题（可选）

    Returns:
        JSON 字符串：{summary: str, chart_path: str|null, stats: {...}}
    """
    if analysis_type not in ANALYSIS_TYPES:
        return json.dumps({
            "summary": f"不支持的分析类型: {analysis_type}。可选: {', '.join(ANALYSIS_TYPES)}",
            "chart_path": None,
            "stats": {},
        }, ensure_ascii=False)

    if not dataset_id:
        return json.dumps({
            "summary": "错误: dataset_id 为必填参数",
            "chart_path": None,
            "stats": {},
        }, ensure_ascii=False)

    # 1. 查询 DataDownload
    try:
        async with AsyncSessionLocal() as session:
            result = await download_dao.list_by_dataset(session, dataset_id, page=1, size=1)
            if not result.get("ok") or not result.get("items"):
                return json.dumps({
                    "summary": f"数据集 {dataset_id[:12]}… 尚未上传数据文件，无法分析",
                    "chart_path": None,
                    "stats": {},
                }, ensure_ascii=False)

            download = result["items"][0]
            file_path = download["file_path"]
            file_format = download["file_format"]
    except Exception as e:
        logger.error("[data_analysis_tool] DB query failed: {}", e)
        return json.dumps({
            "summary": f"查询数据文件失败: {e}",
            "chart_path": None,
            "stats": {},
        }, ensure_ascii=False)

    # 2. 读取数据文件
    try:
        df = await asyncio.to_thread(_safe_read_df, file_path, file_format)
    except Exception as e:
        logger.error("[data_analysis_tool] read file failed: {} — {}", file_path, e)
        return json.dumps({
            "summary": f"读取数据文件失败: {e}",
            "chart_path": None,
            "stats": {},
        }, ensure_ascii=False)

    if df.empty:
        return json.dumps({
            "summary": "数据文件为空",
            "chart_path": None,
            "stats": {},
        }, ensure_ascii=False)

    # 3. 执行分析
    analysis_funcs = {
        "describe": _analysis_describe,
        "value_counts": _analysis_value_counts,
        "groupby": _analysis_groupby,
        "corr_matrix": _analysis_corr,
        "null_analysis": _analysis_nulls,
    }

    try:
        func = analysis_funcs.get(analysis_type)
        if func:
            analysis_result = func(
                df,
                columns=columns,
                group_col=group_col,
                agg_col=agg_col,
                agg_func=agg_func,
            )
        else:
            # 图表类型：先做 describe，再渲染图表
            describe_result = _analysis_describe(df)
            analysis_result = describe_result
    except Exception as e:
        logger.error("[data_analysis_tool] analysis failed for {}: {}", analysis_type, e)
        return json.dumps({
            "summary": f"分析失败: {e}",
            "chart_path": None,
            "stats": {},
        }, ensure_ascii=False)

    # 4. 渲染图表（在 executor 线程中）
    chart_path: str | None = None
    chart_types = {"histogram", "bar_chart", "line_chart", "scatter", "pie_chart"}
    if analysis_type in chart_types:
        try:
            output_dir = str(_CHARTS_DIR / dataset_id)
            chart_path = await asyncio.to_thread(
                _render_chart,
                df,
                analysis_type,
                columns=columns,
                group_col=group_col,
                agg_col=agg_col,
                agg_func=agg_func,
                bins=bins,
                chart_title=chart_title,
                output_dir=output_dir,
            )
        except Exception as e:
            logger.warning("[data_analysis_tool] chart render error: {}", e)

    # 5. 返回结果
    return json.dumps({
        "summary": analysis_result.get("summary", ""),
        "chart_path": chart_path,
        "stats": analysis_result.get("stats", {}),
        "columns": df.columns.tolist()[:20],
        "shape": list(df.shape),
    }, ensure_ascii=False, default=str)


__all__ = ["ANALYSIS_TYPES", "analyze_and_chart"]
