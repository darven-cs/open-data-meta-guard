"""数据质量评估 service 层。

evaluate_data(session, data_download_id):
    1. 读 data_download → 获取文件路径
    2. 调 quality_tool.assess_quality()
    2.5 调 semantic agent 做语义层评估（容错，失败不阻塞）
    3. 合并结构+语义结果，写 data_quality_evaluations 记录
    4. 返回 evaluation dict
"""
import os

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import logger
from app.dao import data_download as dl_dao
from app.dao import data_quality_evaluation as dq_dao
from app.agents.data_quality_assess import build_quality_report


async def evaluate_data(
    session: AsyncSession,
    data_download_id: int,
) -> dict:
    """同步执行数据质量评估并入库。

    Returns:
        {"ok": True, "evaluation_id": int, "evaluation": dict}
        {"ok": False, "error": "..."}
    """
    # 1) 读 data_download 记录
    dl_res = await dl_dao.get_by_id(session, data_download_id)
    if not dl_res.get("ok"):
        return dl_res
    dl = dl_res["download"]

    # 2) 调 quality_tool
    logger.info(
        "[data_quality] evaluating download_id=%d file=%s format=%s",
        data_download_id, dl["file_name"], dl["file_format"],
    )
    try:
        result = build_quality_report(dl["file_path"], dl["dataset_id"])
    except Exception as e:
        logger.exception("[data_quality] quality tool failed for download_id=%d", data_download_id)
        return {"ok": False, "error": f"quality assessment failed: {e}"}

    # 2.5) 读 DataFrame 用于语义评估
    df = _read_dataframe(dl["file_path"])
    semantic_result = await _run_semantic_eval(df, result, dl["file_name"])

    # 合并结构 + 语义结果
    merged_issues = list(result["issues"])
    merged_summary = dict(result["summary"])
    report_md = result["report_markdown"]

    if semantic_result:
        merged_issues += _format_semantic_issues(semantic_result)
        merged_summary.update(_format_semantic_scores(semantic_result))
        report_md = _append_semantic_report(report_md, semantic_result)

    # 3) 写 evaluation 记录
    create_res = await dq_dao.create_evaluation(
        session=session,
        dataset_id=dl["dataset_id"],
        data_download_id=data_download_id,
        evaluation_content=report_md,
        summary=merged_summary,
        issues=merged_issues,
    )
    if not create_res.get("ok"):
        return create_res

    eval_id = create_res["evaluation_id"]

    # 4) 读回完整记录
    get_res = await dq_dao.get_evaluation(session, eval_id)
    if not get_res.get("ok"):
        return get_res

    logger.info("[data_quality] evaluation created: id=%d", eval_id)
    return {"ok": True, "evaluation_id": eval_id, "evaluation": get_res["evaluation"]}


async def list_evaluations(
    session: AsyncSession,
    dataset_id: str,
    page: int = 1,
    size: int = 20,
) -> dict:
    """按 dataset_id 列评估历史。"""
    return await dq_dao.list_evaluations(
        session=session,
        dataset_id=dataset_id,
        page=page,
        size=size,
    )


async def list_downloads_with_evaluation(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> dict:
    """data_downloads + 最新 quality eval 摘要。"""
    return await dq_dao.list_downloads_with_latest_evaluation(
        session=session,
        page=page,
        size=size,
    )


# ──────────────────────── 语义评估辅助函数 ────────────────────────


def _read_dataframe(file_path: str) -> "pd.DataFrame | None":
    """读取文件为 DataFrame，用于语义评估。"""
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    fmt = ext
    if fmt == "xls":
        fmt = "xlsx"
    try:
        if fmt == "csv":
            return pd.read_csv(file_path)
        elif fmt in ("xlsx", "xls"):
            return pd.read_excel(file_path)
        elif fmt == "json":
            return pd.read_json(file_path)
        else:
            logger.warning("[data_quality] unsupported format for semantic eval: %s", fmt)
            return None
    except Exception as e:
        logger.warning("[data_quality] failed to read file for semantic eval: %s", e)
        return None


def _build_semantic_payload(
    df: "pd.DataFrame",
    structural_result: dict,
    file_name: str,
) -> str:
    """组装语义评估 agent 的输入文本。"""
    lines: list[str] = []
    lines.append(f"## 文件信息\n文件名: {file_name}\n")

    # 列信息
    lines.append("## 列信息\n")
    lines.append("| 列名 | 数据类型 | 非空数 | 唯一值数 | 样例值 |")
    lines.append("|------|----------|--------|----------|--------|")
    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = df[col].notna().sum()
        nunique = df[col].nunique(dropna=True)
        samples = df[col].dropna().unique()[:3].tolist()
        sample_str = ", ".join(str(s) for s in samples)[:60]
        lines.append(f"| {col} | {dtype} | {non_null} | {nunique} | {sample_str} |")
    lines.append("")

    # 前 50 行样本
    lines.append("## 数据样本（前 50 行）\n")
    lines.append(df.head(50).to_csv(index=True))
    lines.append("")

    # 结构检查摘要
    lines.append("## 结构检查摘要\n")
    s = structural_result["summary"]
    lines.append(f"- 行数: {s.get('n', '?')} | 列数: {s.get('p', '?')}")
    lines.append(f"- 缺失值: {s.get('n_missing', '?')} ({s.get('p_missing', '?')}%)")
    lines.append(f"- 重复行: {s.get('n_duplicates', '?')} ({s.get('p_duplicates', '?')}%)")
    lines.append("")

    if structural_result.get("issues"):
        lines.append("### 结构检查已发现的问题（请勿重复报告）：\n")
        for issue in structural_result["issues"]:
            lines.append(f"- [{issue.get('severity', '?')}] {issue.get('check', '?')}: {issue.get('detail', '?')}")
        lines.append("")

    return "\n".join(lines)


async def _run_semantic_eval(
    df: "pd.DataFrame | None",
    structural_result: dict,
    file_name: str,
) -> dict | None:
    """运行语义层 LLM 评估（容错：失败返回 None）。"""
    if df is None or df.empty:
        logger.info("[data_quality] skipping semantic eval: no data")
        return None

    try:
        from app.agents.data_quality_semantic import build as build_semantic_agent

        agent = build_semantic_agent()
        if agent is None:
            logger.warning("[data_quality] semantic agent build returned None")
            return None

        payload = _build_semantic_payload(df, structural_result, file_name)
        # trunk-ignore(bandit/B201)
        result = await agent.ainvoke({"input": payload})

        # with_structured_output chain 直接返回 SemanticQualityOutput 实例
        if hasattr(result, "model_dump"):
            return result.model_dump()
        elif isinstance(result, dict):
            if "dimension_scores" in result or "issues" in result:
                return result
            return None
    except Exception as e:
        logger.warning("[data_quality] semantic eval failed: %s", e)
        return None


def _format_semantic_issues(semantic_result: dict) -> list[dict]:
    """将语义 issue 转为标准 issue 格式，加 source / category 标签。"""
    issues = semantic_result.get("issues", [])
    formatted: list[dict] = []
    for iss in issues:
        formatted.append({
            "source": "semantic",
            "category": iss.get("category", ""),
            "severity": iss.get("severity", "info"),
            "dimension": iss.get("dimension", ""),
            "field": iss.get("field"),
            "check": f"[语义][{iss.get('category', '')}] {iss.get('dimension', '')}",
            "detail": iss.get("description", ""),
            "suggestion": iss.get("suggestion", ""),
        })
    return formatted


def _format_semantic_scores(semantic_result: dict) -> dict:
    """将语义维度评分转为 summary 中的字段。"""
    scores = semantic_result.get("dimension_scores", {})
    return {
        "completeness_score": scores.get("completeness", 100),
        "consistency_score": scores.get("consistency", 100),
        "accuracy_score": scores.get("accuracy", 100),
        "timeliness_score": scores.get("timeliness", 100),
        "uniqueness_score": scores.get("uniqueness", 100),
        "normativity_score": scores.get("normativity", 100),
        "openness_score": scores.get("openness", 100),
        "security_score": scores.get("security", 100),
        "overall_score": semantic_result.get("overall_score", 100),
    }


def _append_semantic_report(report_md: str, semantic_result: dict) -> str:
    """在 markdown 报告末尾追加语义评估章节。"""
    lines: list[str] = []
    lines.append("\n---\n")
    lines.append("## 语义层数据质量评估（LLM）\n")

    scores = semantic_result.get("dimension_scores", {})
    lines.append("### 8 维度评分\n")
    lines.append("| 维度 | 评分 |")
    lines.append("|------|------|")
    dim_labels = {
        "completeness": "完整性",
        "consistency": "一致性",
        "accuracy": "准确性",
        "timeliness": "时效性",
        "uniqueness": "唯一性",
        "normativity": "规范性",
        "openness": "开放性",
        "security": "安全性/隐私性",
    }
    for key, label in dim_labels.items():
        score = scores.get(key, "?")
        lines.append(f"| {label} | {score}/100 |")
    lines.append("")

    overall = semantic_result.get("overall_score", "?")
    lines.append(f"**综合语义质量评分**: {overall}/100\n")

    issues = semantic_result.get("issues", [])
    if issues:
        lines.append("### 语义层问题\n")
        for iss in issues:
            sev = iss.get("severity", "info")
            cat = iss.get("category", "")
            dim = iss.get("dimension", "")
            desc = iss.get("description", "")
            sug = iss.get("suggestion", "")
            lines.append(f"- **[{sev.upper()}][{cat}]** ({dim}) {desc}")
            if sug:
                lines.append(f"  - 建议: {sug}")
        lines.append("")

    summary = semantic_result.get("summary", "")
    if summary:
        lines.append(f"### 评估结论\n{summary}\n")

    return report_md + "\n".join(lines)
