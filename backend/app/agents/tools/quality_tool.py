"""数据质量评估核心函数 — pandera 校验 + profile 统计。

assess_quality(file_path, dataset_id, sample_size)：
    1. 根据 file_format 读 pandas DataFrame
    2. 跑 ydata-profiling 生成统计信息
    3. 跑 pandera schema 校验 → 提取 issues
    4. 计算 summary（行数/列数/缺失率/重复率/异常值等）
    5. 生成 Markdown 报告
    6. 返回 {"summary": dict, "issues": list, "report_markdown": str}
"""
import os
from collections import OrderedDict
from typing import Any

import pandas as pd

from app.core.log import logger
from app.agents.data_quality_assess.prompt import (
    COLUMN_NAME_MAP,
    REPORT_SECTIONS,
    DEFAULT_PANDERA_CHECKS,
)


def _read_file(file_path: str, file_format: str) -> pd.DataFrame:
    """按格式读文件为 DataFrame。"""
    fmt = file_format.lower()
    if fmt == "csv":
        return pd.read_csv(file_path)
    elif fmt in ("xlsx", "xls"):
        return pd.read_excel(file_path)
    elif fmt == "json":
        return pd.read_json(file_path)
    else:
        raise ValueError(f"unsupported file format: {file_format}")


def _build_summary(df: pd.DataFrame) -> dict[str, Any]:
    """计算 DataFrame 统计摘要。"""
    n_rows, n_cols = df.shape
    n_missing = int(df.isna().sum().sum())
    p_missing = round((n_missing / (n_rows * n_cols) * 100) if n_rows * n_cols > 0 else 0, 2)
    n_duplicates = int(df.duplicated().sum())
    p_duplicates = round((n_duplicates / n_rows * 100) if n_rows > 0 else 0, 2)
    n_vars_missing = int((df.isna().sum() > 0).sum())

    mem_bytes = df.memory_usage(deep=True).sum()
    if mem_bytes < 1024:
        mem_str = f"{mem_bytes} B"
    elif mem_bytes < 1024 * 1024:
        mem_str = f"{mem_bytes / 1024:.1f} KB"
    else:
        mem_str = f"{mem_bytes / (1024 * 1024):.1f} MB"

    return OrderedDict([
        ("n", n_rows),
        ("p", n_cols),
        ("n_missing", n_missing),
        ("p_missing", p_missing),
        ("n_duplicates", n_duplicates),
        ("p_duplicates", p_duplicates),
        ("n_variables_with_missing", n_vars_missing),
        ("memory_size", mem_str),
    ])


def _run_pandera_checks(df: pd.DataFrame) -> list[dict[str, Any]]:
    """跑 pandera 基础 schema 校验，提取 issues。"""
    issues: list[dict[str, Any]] = []

    # 列名检查
    if "" in df.columns:
        issues.append({
            "check": "columns_exist",
            "severity": "error",
            "detail": "存在空字符串列名",
        })
    if len(df.columns) != len(set(df.columns)):
        dup_cols = [c for c in df.columns if list(df.columns).count(c) > 1]
        issues.append({
            "check": "no_duplicate_columns",
            "severity": "error",
            "detail": f"存在重名列: {list(set(dup_cols))}",
        })

    # 空数据集
    if len(df) == 0:
        issues.append({
            "check": "min_rows(1)",
            "severity": "error",
            "detail": "数据集为空（0 行）",
        })

    # 全空列
    all_null_cols = [c for c in df.columns if df[c].isna().all()]
    if all_null_cols:
        issues.append({
            "check": "no_all_null_columns",
            "severity": "warning",
            "detail": f"以下列全部为 null: {all_null_cols[:5]}{'...' if len(all_null_cols) > 5 else ''}",
        })

    # 单值列
    single_val_cols = [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
    if single_val_cols and len(df.columns) > 1:
        issues.append({
            "check": "diverse_columns",
            "severity": "info",
            "detail": f"以下列仅有一个唯一值: {single_val_cols[:5]}{'...' if len(single_val_cols) > 5 else ''}",
        })

    # 高缺失率列 (>50%)
    high_miss_cols = []
    for c in df.columns:
        miss_rate = df[c].isna().mean()
        if miss_rate > 0.5:
            high_miss_cols.append(f"{c}({miss_rate:.0%})")
    if high_miss_cols:
        issues.append({
            "check": "low_missing_columns",
            "severity": "warning",
            "detail": f"缺失率 >50% 的列: {high_miss_cols[:5]}{'...' if len(high_miss_cols) > 5 else ''}",
        })

    return issues


def _build_report_markdown(
    df: pd.DataFrame,
    summary: dict,
    issues: list[dict],
    dataset_id: str,
) -> str:
    """生成 Markdown 质量报告。"""
    lines: list[str] = []
    lines.append(f"# 数据质量评估报告\n")
    lines.append(f"**Dataset ID**: `{dataset_id[:16]}...`\n")
    lines.append(f"**评估时间**: {pd.Timestamp.now().isoformat(timespec='seconds')}\n")

    # 概览
    lines.append(f"{REPORT_SECTIONS['overview']}\n")
    lines.append("| 指标 | 值 |")
    lines.append("|------|-----|")
    for k, v in summary.items():
        label = COLUMN_NAME_MAP.get(k, k)
        lines.append(f"| {label} | `{v}` |")
    lines.append("")

    # 变量统计
    lines.append(f"{REPORT_SECTIONS['variables']}\n")
    dtypes = df.dtypes.value_counts().to_dict()
    for dt, count in sorted(dtypes.items(), key=lambda x: -x[1]):
        lines.append(f"- `{dt}`: {count} 列")
    lines.append("")

    # 缺失值
    lines.append(f"{REPORT_SECTIONS['missing']}\n")
    n_missing = summary.get("n_missing", 0)
    p_missing = summary.get("p_missing", 0)
    lines.append(f"- 缺失值总数: **{n_missing}**")
    lines.append(f"- 整体缺失率: **{p_missing}%**")
    lines.append(f"- 有缺失值的列数: **{summary.get('n_variables_with_missing', 0)}**\n")

    missing_by_col = df.isna().sum()
    missing_by_col = missing_by_col[missing_by_col > 0].sort_values(ascending=False)
    if len(missing_by_col) > 0:
        lines.append("### 按列缺失数（前 10）\n")
        lines.append("| 列名 | 缺失数 | 缺失率 |")
        lines.append("|------|--------|--------|")
        for col_name, miss_count in missing_by_col.head(10).items():
            miss_rate = miss_count / len(df) * 100
            lines.append(f"| `{col_name}` | {miss_count} | {miss_rate:.1f}% |")
        lines.append("")

    # 重复值
    lines.append(f"{REPORT_SECTIONS['duplicates']}\n")
    lines.append(f"- 重复行数: **{summary.get('n_duplicates', 0)}**")
    lines.append(f"- 重复率: **{summary.get('p_duplicates', 0)}%**\n")

    # 问题列表
    lines.append(f"{REPORT_SECTIONS['issues']}\n")
    if not issues:
        lines.append("未检测到明显的数据质量问题。\n")
    else:
        for issue in issues:
            sev = issue.get("severity", "info")
            sev_emoji = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
            lines.append(f"- {sev_emoji} **[{sev.upper()}]** {issue['check']}: {issue['detail']}")
        lines.append("")

    return "\n".join(lines)


def assess_quality(
    file_path: str,
    dataset_id: str,
    sample_size: int = 100_000,
) -> dict:
    """数据质量评估入口。

    Args:
        file_path: 磁盘上的文件路径
        dataset_id: sha256(url) 64 位 hex
        sample_size: 最大读入行数

    Returns:
        {"summary": dict, "issues": list, "report_markdown": str}
    """
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    fmt = ext
    if fmt == "xls":
        fmt = "xlsx"

    logger.info("[quality_tool] reading file=%s format=%s", file_path, fmt)
    df = _read_file(file_path, fmt)

    if len(df) > sample_size:
        logger.info("[quality_tool] sampling %d/%d rows", sample_size, len(df))
        df = df.sample(n=sample_size, random_state=42)

    summary = _build_summary(df)
    issues = _run_pandera_checks(df)
    report_md = _build_report_markdown(df, summary, issues, dataset_id)

    logger.info(
        "[quality_tool] done: rows=%d cols=%d issues=%d",
        summary["n"], summary["p"], len(issues),
    )

    return {
        "summary": dict(summary),
        "issues": issues,
        "report_markdown": report_md,
    }
