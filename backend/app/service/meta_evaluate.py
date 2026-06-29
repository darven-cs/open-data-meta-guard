"""元数据评估 service 层（v2.0 async + tracing）。

设计：
- evaluate_with_tracing()  异步 worker 调用入口，含阶段埋点 / 超时 / 取消 / token 统计
- evaluate_dataset()        保留为内部 helper（被 evaluate_with_tracing 调用）
- list_evaluations()        历史评估列表（路由层透传）
"""
import asyncio
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.log import logger
from app.dao import dataset as dataset_dao
from app.dao import meta_evaluation as meta_eval_dao
from app.dao import meta_evaluation_job as job_dao
from app.agents.meta_evaluate.schema import (
    EU_MQA_DIMENSION_MAX,
    EU_MQA_RULE_KEYS,
    EU_MQA_RULE_MAX,
)


REASONING_TRUNCATE_BYTES = settings.meta_evaluate_log_truncate_bytes


# ──────────────────────── public ────────────────────────


async def evaluate_with_tracing(
    dataset_id: str,
    job_id: int,
) -> dict[str, Any]:
    """异步评估主流程（worker 调度执行）。

    阶段埋点：
        load_dataset → build_agent → invoke_agent → normalize
        → build_report → create_evaluation

    Args:
        dataset_id: sha256(url) 64 位 hex
        job_id: meta_evaluation_jobs.id

    Returns:
        {"ok": True, "evaluation_id", "stats": {...}}
        {"ok": False, "error", "stats": {...}}
    """
    stats: dict[str, Any] = {
        "phase_ms": {},
        "tool_calls": [],
        "reasoning_chunks": 0,
        "token_prompt": None,
        "token_completion": None,
        "token_total": None,
    }
    total_start = time.monotonic()

    def _elapsed_ms_since(start: float) -> int:
        return int((time.monotonic() - start) * 1000)

    async def _phase(name: str, fn):
        """阶段埋点：自动算 elapsed_ms，写日志。"""
        logger.info("[meta-evaluate] job={} phase={} started", job_id, name)
        t = time.monotonic()
        try:
            result = await fn()
            stats["phase_ms"][name] = _elapsed_ms_since(t)
            logger.info(
                "[meta-evaluate] job={} phase={} elapsed_ms={}",
                job_id, name, stats["phase_ms"][name],
            )
            return result
        except Exception as e:
            stats["phase_ms"][name] = _elapsed_ms_since(t)
            logger.exception(
                "[meta-evaluate] job={} phase={} failed elapsed_ms={}",
                job_id, name, stats["phase_ms"][name],
            )
            raise

    async with AsyncSessionLocal() as session:
        # 0a) 读 job 拿预分配的 evaluation_id（UUID4）
        job_res = await job_dao.get_job(session=session, job_id=job_id)
        if not job_res.get("ok"):
            await _write_failed(
                job_id, f"get_job failed: {job_res.get('error', 'unknown')}",
                stats, _elapsed_ms_since(total_start),
            )
            return {"ok": False, "error": "job not found", "stats": stats}
        preallocated_id = job_res["job"].get("evaluation_id")
        if not preallocated_id:
            await _write_failed(
                job_id, "job missing preallocated evaluation_id",
                stats, _elapsed_ms_since(total_start),
            )
            return {"ok": False, "error": "job missing evaluation_id", "stats": stats}

        # 0b) load_dataset
        async def _load():
            ds_res = await dataset_dao.get_dataset(session=session, dataset_id=dataset_id)
            if not ds_res.get("ok"):
                raise ValueError(ds_res.get("error", "dataset not found"))
            return ds_res["dataset"]

        try:
            dataset = await _phase("load_dataset", _load)
        except Exception as e:
            await _write_failed(job_id, f"load_dataset failed: {e}", stats, _elapsed_ms_since(total_start))
            return {"ok": False, "error": str(e), "stats": stats}

        metadata = dataset.get("metadata") or {}
        payload = json.dumps(
            {"dataset_id": dataset_id, "metadata": metadata},
            ensure_ascii=False,
        )

        # 1) build_agent
        from app.agents.meta_evaluate.builder import build as build_meta_evaluate_agent

        async def _build():
            return build_meta_evaluate_agent()

        try:
            agent = await _phase("build_agent", _build)
        except Exception as e:
            await _write_failed(job_id, f"build_agent failed: {e}", stats, _elapsed_ms_since(total_start))
            return {"ok": False, "error": str(e), "stats": stats}

        # 2) invoke_agent（带超时）
        timeout = settings.meta_evaluate_timeout_sec
        eval_timestamp = datetime.now(timezone.utc).isoformat()
        t_invoke = time.monotonic()
        logger.info(
            "[meta-evaluate] job={} phase=invoke_agent started timeout={}s",
            job_id, timeout,
        )
        try:
            raw_result = await asyncio.wait_for(
                agent.ainvoke(
                    {"messages": [{"role": "user", "content": payload}]},
                    config={"recursion_limit": settings.meta_evaluate_agent_recursion_limit},
                ),
                timeout=timeout,
            )
        except asyncio.CancelledError:
            elapsed = _elapsed_ms_since(total_start)
            logger.info(
                "[meta-evaluate] job={} status=cancelled by user request elapsed_ms={}",
                job_id, elapsed,
            )
            await _write_cancelled(job_id, "cancelled by user", stats, elapsed)
            return {"ok": False, "error": "cancelled", "stats": stats}
        except asyncio.TimeoutError:
            elapsed = _elapsed_ms_since(total_start)
            stats["phase_ms"]["invoke_agent"] = _elapsed_ms_since(t_invoke)
            logger.warning(
                "[meta-evaluate] job={} phase=invoke_agent timeout={}s",
                job_id, timeout,
            )
            err = f"agent timeout after {timeout}s"
            await _write_failed(job_id, err, stats, elapsed)
            return {"ok": False, "error": err, "stats": stats}
        except Exception as e:
            # GraphRecursionError 是 agent 在 config.recursion_limit 步内没走到终止条件
            # （多半是 LLM 反复调 tool 但从不调 MetaEvaluateResult 返回）
            from langgraph.errors import GraphRecursionError
            if isinstance(e, GraphRecursionError):
                elapsed = _elapsed_ms_since(total_start)
                stats["phase_ms"]["invoke_agent"] = _elapsed_ms_since(t_invoke)
                logger.warning(
                    "[meta-evaluate] job={} phase=invoke_agent recursion_limit={} reached without stop",
                    job_id, settings.meta_evaluate_agent_recursion_limit,
                )
                err = (
                    f"agent recursion_limit={settings.meta_evaluate_agent_recursion_limit} "
                    "reached without hitting MetaEvaluateResult"
                )
                await _write_failed(job_id, err, stats, elapsed)
                return {"ok": False, "error": err, "stats": stats}
            elapsed = _elapsed_ms_since(total_start)
            stats["phase_ms"]["invoke_agent"] = _elapsed_ms_since(t_invoke)
            tb = traceback.format_exc(limit=3)
            logger.exception(
                "[meta-evaluate] job={} phase=invoke_agent failed: {}", job_id, e,
            )
            await _write_failed(
                job_id,
                f"agent failed: {type(e).__name__}: {e} | {tb}",
                stats,
                elapsed,
            )
            return {"ok": False, "error": str(e), "stats": stats}

        stats["phase_ms"]["invoke_agent"] = _elapsed_ms_since(t_invoke)
        logger.info(
            "[meta-evaluate] job={} phase=invoke_agent elapsed_ms={}",
            job_id, stats["phase_ms"]["invoke_agent"],
        )

        # 抽取 tool_calls / reasoning_content / usage_metadata
        try:
            _extract_messages(raw_result, stats)
        except Exception as e:
            logger.warning(
                "[meta-evaluate] job={} extract_messages failed: {}", job_id, e,
            )

        eval_result = raw_result.get("structured_response")
        if eval_result is None:
            err = "agent returned no structured_response"
            await _write_failed(job_id, err, stats, _elapsed_ms_since(total_start))
            return {"ok": False, "error": err, "stats": stats}

        # 3) normalize
        async def _normalize():
            return _normalize_rule_scores(dict(eval_result.rule_scores or {}))

        try:
            rule_scores = await _phase("normalize", _normalize)
        except Exception as e:
            await _write_failed(job_id, f"normalize failed: {e}", stats, _elapsed_ms_since(total_start))
            return {"ok": False, "error": str(e), "stats": stats}

        # 4) build_report
        async def _build_report():
            return _build_markdown_report(
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

        try:
            markdown = await _phase("build_report", _build_report)
        except Exception as e:
            await _write_failed(job_id, f"build_report failed: {e}", stats, _elapsed_ms_since(total_start))
            return {"ok": False, "error": str(e), "stats": stats}

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

        # 5) create_evaluation（用新 session，因为上一个 session 可能因失败 rollback 过）
        async with AsyncSessionLocal() as write_session:
            async def _create():
                return await meta_eval_dao.create_evaluation(
                    session=write_session,
                    evaluation_id=preallocated_id,
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

            try:
                create_res = await _phase("create_evaluation", _create)
            except Exception as e:
                await _write_failed(
                    job_id, f"create_evaluation failed: {e}", stats, _elapsed_ms_since(total_start),
                )
                return {"ok": False, "error": str(e), "stats": stats}

            if not create_res.get("ok"):
                err = create_res.get("error", "create_evaluation failed")
                await _write_failed(job_id, err, stats, _elapsed_ms_since(total_start))
                return {"ok": False, "error": err, "stats": stats}

            evaluation_id = create_res["evaluation_id"]
            logger.info(
                "[meta-evaluate] job={} phase=create_evaluation evaluation_id={}",
                job_id, evaluation_id,
            )

        # 6) 写终态 completed
        total_elapsed = _elapsed_ms_since(total_start)
        await _write_completed(
            job_id, evaluation_id, stats, total_elapsed,
        )
        logger.info(
            "[meta-evaluate] job={} status=completed total_elapsed_ms={}",
            job_id, total_elapsed,
        )

        return {
            "ok": True,
            "evaluation_id": evaluation_id,
            "dataset_id": dataset_id,
            "score_total": int(eval_result.score_total),
            "grade": str(eval_result.grade),
            "stats": stats,
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


# ──────────────────────── 内部 helper ────────────────────────


async def _write_completed(
    job_id: int,
    evaluation_id: str,
    stats: dict,
    elapsed_ms: int,
) -> None:
    async with AsyncSessionLocal() as session:
        await job_dao.mark_completed(
            session,
            job_id,
            evaluation_id,
            elapsed_ms=elapsed_ms,
            token_prompt=stats.get("token_prompt"),
            token_completion=stats.get("token_completion"),
            token_total=stats.get("token_total"),
            tool_calls_json=stats.get("tool_calls") or None,
            reasoning_log=_truncate_str(_join_reasoning(stats), REASONING_TRUNCATE_BYTES),
        )


async def _write_failed(
    job_id: int,
    error: str,
    stats: dict,
    elapsed_ms: int,
) -> None:
    async with AsyncSessionLocal() as session:
        await job_dao.mark_failed(
            session,
            job_id,
            error,
            elapsed_ms=elapsed_ms,
            token_prompt=stats.get("token_prompt"),
            token_completion=stats.get("token_completion"),
            token_total=stats.get("token_total"),
            tool_calls_json=stats.get("tool_calls") or None,
            reasoning_log=_truncate_str(_join_reasoning(stats), REASONING_TRUNCATE_BYTES),
        )


async def _write_cancelled(
    job_id: int,
    error: str,
    stats: dict,
    elapsed_ms: int,
) -> None:
    async with AsyncSessionLocal() as session:
        await job_dao.mark_cancelled(
            session,
            job_id,
            error=error,
            elapsed_ms=elapsed_ms,
        )


def _extract_messages(result: dict[str, Any], stats: dict) -> None:
    """从 agent.ainvoke() 结果抽取 tool_calls / reasoning_content / usage_metadata。"""
    messages = result.get("messages") or []
    tool_calls: list[dict] = []
    reasoning_chunks: list[str] = []
    token_prompt = None
    token_completion = None
    token_total = None

    for m in messages:
        # AIMessage
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                if isinstance(tc, dict):
                    name = tc.get("name") or tc.get("type", "")
                    args = tc.get("args", {})
                    tool_calls.append({"name": name, "args": args})
                    logger.info(
                        "[meta-evaluate] job={} tool_call name={} args={}",
                        "?", name, _truncate_str(repr(args), 512),
                    )
                else:
                    name = getattr(tc, "name", "")
                    args = getattr(tc, "args", {})
                    tool_calls.append({"name": name, "args": args})
                    logger.info(
                        "[meta-evaluate] job={} tool_call name={} args={}",
                        "?", name, _truncate_str(repr(args), 512),
                    )

        # reasoning_content（DeepSeek 思考内容在 additional_kwargs）
        rc = None
        if hasattr(m, "additional_kwargs"):
            rc = (m.additional_kwargs or {}).get("reasoning_content")
        if rc:
            reasoning_chunks.append(str(rc))

        # usage_metadata 通常挂在最后一条 AIMessage 上
        usage = getattr(m, "usage_metadata", None)
        if usage and isinstance(usage, dict):
            token_prompt = usage.get("input_tokens") or usage.get("prompt_tokens") or token_prompt
            token_completion = usage.get("output_tokens") or usage.get("completion_tokens") or token_completion
            token_total = usage.get("total_tokens") or token_total
        elif usage and hasattr(usage, "input_tokens"):
            token_prompt = usage.input_tokens
            token_completion = getattr(usage, "output_tokens", None)
            token_total = getattr(usage, "total_tokens", None)

    stats["tool_calls"] = tool_calls
    stats["reasoning_chunks"] = len(reasoning_chunks)
    stats["reasoning_parts"] = reasoning_chunks
    stats["token_prompt"] = token_prompt
    stats["token_completion"] = token_completion
    stats["token_total"] = token_total

    for i, chunk in enumerate(reasoning_chunks, 1):
        logger.info(
            "[meta-evaluate] reasoning[{}] ({}B): {}",
            i, len(chunk.encode("utf-8")), _truncate_str(chunk, 256),
        )

    if token_prompt is not None or token_completion is not None or token_total is not None:
        logger.info(
            "[meta-evaluate] token prompt={} completion={} total={}",
            token_prompt, token_completion, token_total,
        )


def _join_reasoning(stats: dict) -> str:
    parts = stats.get("reasoning_parts") or []
    if not parts:
        return ""
    return "\n\n---\n\n".join(parts)


def _truncate_str(s: str | None, max_bytes: int) -> str | None:
    if s is None:
        return None
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s
    return b[:max_bytes].decode("utf-8", errors="ignore") + "...(truncated)"


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

    lines.append("## 总览")
    lines.append("")
    lines.append(f"- **总分**: **{score_total} / 405**")
    lines.append(f"- **评级**: **{grade}**")
    lines.append("")

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

    lines.append("## 23 条 indicator 明细")
    lines.append("")
    lines.append("| Indicator | 得分 | 满分 |")
    lines.append("|---|---|---|")
    for key in EU_MQA_RULE_KEYS:
        mx = EU_MQA_RULE_MAX[key]
        lines.append(f"| `{key}` | {rule_scores.get(key, 0)} | {mx} |")
    lines.append("")

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

    lines.append("## 结论")
    lines.append("")
    lines.append(summary or "（无）")
    lines.append("")

    return "\n".join(lines)