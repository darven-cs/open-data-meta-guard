"""元数据评估 service 层（v2.0 同步实现）。

设计要点：
- 同步触发 meta_evaluate agent 跑一次评估（agent 调 3 个 observation tool）
- 成功后落库 meta_evaluations 表 + 生成 Markdown 报告
- 失败返回 {"ok": False, "error": "..."}（路由层负责 HTTP 状态码映射）
- 每次调用 build() 新建 agent 实例（避免 state 污染）
- session 由调用方（路由层 Depends(get_db)）注入
"""
import json
import traceback
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import logger
from app.dao import dataset as dataset_dao
from app.dao import meta_evaluation as meta_eval_dao
from app.agents.meta_evaluate.schema import (
    EU_MQA_DIMENSION_MAX,
    EU_MQA_RULE_KEYS,
    EU_MQA_RULE_MAX,
)


# ──────────────────────── public ────────────────────────


async def evaluate_dataset(
    session: AsyncSession,
    dataset_id: str,
) -> dict[str, Any]:
    """对一条已采集的 dataset 跑 EU MQA 评估并落库。

    Args:
        session: 由 Depends(get_db) 注入
        dataset_id: sha256(url) 64 位 hex

    Returns:
        {"ok": True, "evaluation_id", "score_total", "grade", "created_at"}
        {"ok": False, "error": "..."}
    """
    # 1) 拿 dataset（不存在 → 直接返错）
    ds_res = await dataset_dao.get_dataset(session=session, dataset_id=dataset_id)
    if not ds_res.get("ok"):
        return {"ok": False, "error": ds_res.get("error", "dataset not found")}
    dataset = ds_res["dataset"]
    metadata = dataset.get("metadata") or {}

    # 2) 构造 LLM 输入（payload 给 agent user message）
    payload = json.dumps(
        {"dataset_id": dataset_id, "metadata": metadata},
        ensure_ascii=False,
    )

    # 3) 延迟 import + 每次新建 agent 实例
    from app.agents.meta_evaluate.builder import build as build_meta_evaluate_agent

    eval_timestamp = datetime.now(timezone.utc).isoformat()
    try:
        agent = build_meta_evaluate_agent()
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": payload}]}
        )
        eval_result = result.get("structured_response")
        if eval_result is None:
            return {"ok": False, "error": "agent returned no structured_response"}
    except Exception as e:
        tb = traceback.format_exc(limit=3)
        logger.exception("[meta-evaluate] agent failed dataset_id={}: {}", dataset_id, e)
        return {"ok": False, "error": f"agent failed: {type(e).__name__}: {e} | {tb}"}

    # 4) 规整化字段（agent 可能漏填 rule_scores key）
    rule_scores = _normalize_rule_scores(dict(eval_result.rule_scores or {}))

    # 5) 生成 Markdown 报告
    markdown = _build_markdown_report(
        dataset_id=dataset_id,
        score_total=int(eval_result.score_total),
        score_discover=int(eval_result.score_discover),
        score_access=int(eval_result.score_access),
        score_interop=int(eval_result.score_interop),
        score_reuse=int(eval_result.score_reuse),
        score_context=int(eval_result.score_context),
        grade=str(eval_result.grade),
        rule_scores=rule_scores,
        llm_notes=dict(eval_result.llm_notes or {}),
        summary=str(eval_result.summary or ""),
        evaluation_timestamp=eval_timestamp,
    )

    # 6) 落库
    report_json = {
        "score_total": eval_result.score_total,
        "score_discover": eval_result.score_discover,
        "score_access": eval_result.score_access,
        "score_interop": eval_result.score_interop,
        "score_reuse": eval_result.score_reuse,
        "score_context": eval_result.score_context,
        "grade": eval_result.grade,
        "rule_scores": rule_scores,
        "llm_notes": dict(eval_result.llm_notes or {}),
        "summary": eval_result.summary,
        "evaluation_timestamp": eval_timestamp,
    }
    create_res = await meta_eval_dao.create_evaluation(
        session=session,
        dataset_id=dataset_id,
        score_total=int(eval_result.score_total),
        score_discover=int(eval_result.score_discover),
        score_access=int(eval_result.score_access),
        score_interop=int(eval_result.score_interop),
        score_reuse=int(eval_result.score_reuse),
        score_context=int(eval_result.score_context),
        grade=str(eval_result.grade),
        rule_scores=rule_scores,
        llm_notes=dict(eval_result.llm_notes or {}),
        evaluation_content=markdown,
        report_json=report_json,
    )
    if not create_res.get("ok"):
        return {"ok": False, "error": create_res.get("error", "create_evaluation failed")}

    # 7) 回读 created_at
    detail_res = await meta_eval_dao.get_evaluation(
        session=session, evaluation_id=create_res["evaluation_id"]
    )
    created_at = ""
    if detail_res.get("ok"):
        created_at = detail_res["evaluation"].get("created_at") or ""

    return {
        "ok": True,
        "evaluation_id": create_res["evaluation_id"],
        "dataset_id": dataset_id,
        "score_total": int(eval_result.score_total),
        "grade": str(eval_result.grade),
        "created_at": created_at,
    }


async def list_evaluations(
    session: AsyncSession,
    dataset_id: str,
    page: int,
    size: int,
    grade: str = "",
) -> dict[str, Any]:
    """按 dataset_id 拉评估历史 + 可选 grade 过滤。"""
    return await meta_eval_dao.list_evaluations(
        session=session,
        dataset_id=dataset_id,
        page=page,
        size=size,
        grade=grade,
    )


# ──────────────────────── helpers ────────────────────────


def _normalize_rule_scores(raw: dict) -> dict[str, int]:
    """保证 23 个 indicator key 全部存在；缺失补 0；值 int 化。"""
    out: dict[str, int] = {}
    for key in EU_MQA_RULE_KEYS:
        v = raw.get(key, 0)
        try:
            out[key] = int(v)
        except (TypeError, ValueError):
            out[key] = 0
    return out


def _build_markdown_report(
    dataset_id: str,
    score_total: int,
    score_discover: int,
    score_access: int,
    score_interop: int,
    score_reuse: int,
    score_context: int,
    grade: str,
    rule_scores: dict[str, int],
    llm_notes: dict,
    summary: str,
    evaluation_timestamp: str,
) -> str:
    """生成 Markdown 报告（存入 evaluation_content）。"""
    lines: list[str] = []

    short_id = dataset_id[:12]
    lines.append(f"# MQA 评估报告 — `{short_id}…`")
    lines.append("")
    lines.append(f"- **dataset_id**: `{dataset_id}`")
    lines.append(f"- **评估时间**: {evaluation_timestamp}")
    lines.append("")

    # 总分 + 等级
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **总分**: **{score_total} / 405**")
    lines.append(f"- **评级**: **{grade}**")
    lines.append("")

    # 5 维分项
    lines.append("## 5 维分项")
    lines.append("")
    lines.append("| 维度 | 分数 | 满分 |")
    lines.append("|---|---|---|")
    for name_zh, key, score in [
        ("Findability 可发现性", "discover", score_discover),
        ("Accessibility 可访问性", "access", score_access),
        ("Interoperability 互操作性", "interop", score_interop),
        ("Reusability 可重用性", "reuse", score_reuse),
        ("Contextuality 上下文", "context", score_context),
    ]:
        mx = EU_MQA_DIMENSION_MAX[key]
        lines.append(f"| {name_zh} | {score} | {mx} |")
    lines.append("")

    # 23 条规则明细
    lines.append("## 23 条 indicator 明细")
    lines.append("")
    lines.append("| Indicator | 得分 | 满分 |")
    lines.append("|---|---|---|")
    for key in EU_MQA_RULE_KEYS:
        mx = EU_MQA_RULE_MAX[key]
        lines.append(f"| `{key}` | {rule_scores.get(key, 0)} | {mx} |")
    lines.append("")

    # 软评分 + 改进建议
    lines.append("## 软评分")
    lines.append("")
    lines.append(
        f"- **soft_quality_title**: {llm_notes.get('soft_quality_title', '—')} / 5"
    )
    lines.append(
        f"- **soft_quality_description**: {llm_notes.get('soft_quality_description', '—')} / 5"
    )
    lines.append("")

    suggestions = llm_notes.get("improvement_suggestions") or []
    lines.append("## 改进建议")
    lines.append("")
    if isinstance(suggestions, list) and suggestions:
        for s in suggestions:
            lines.append(f"- {s}")
    else:
        lines.append("- （无）")
    lines.append("")

    # 一句话结论
    lines.append("## 结论")
    lines.append("")
    lines.append(summary or "（无）")
    lines.append("")

    return "\n".join(lines)