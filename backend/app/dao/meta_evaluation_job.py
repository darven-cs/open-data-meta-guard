"""meta_evaluation_jobs 表 DAO。

设计要点：
- 函数签名接 Python 类型（str / int / dict），不接 ORM 对象
- 错误统一返回 `{"ok": False, "error": "..."}`；不抛业务异常
- session.commit() 在 DAO 内显式调用
- claim_next_pending 用 `with_for(skip_locked=True)` 保证多 worker 安全
"""
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.meta_evaluation_job import MetaEvaluationJob


# ──────────────────────── helpers ────────────────────────


def _to_dict(job: MetaEvaluationJob) -> dict[str, Any]:
    """ORM → dict（序列化为 API 友好格式）。"""
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "status": job.status,
        "evaluation_id": job.evaluation_id,
        "error": job.error,
        "elapsed_ms": job.elapsed_ms,
        "token_prompt": job.token_prompt,
        "token_completion": job.token_completion,
        "token_total": job.token_total,
        "tool_calls_json": job.tool_calls_json,
        "reasoning_log": job.reasoning_log,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


# ──────────────────────── 公共 ────────────────────────


async def create_job(session: AsyncSession, dataset_id: str) -> dict:
    """新建一条 pending job。"""
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}

    job = MetaEvaluationJob(dataset_id=dataset_id, status="pending")
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return {"ok": True, "job_id": job.id}


async def get_job(session: AsyncSession, job_id: int) -> dict:
    """按 id 查 job。"""
    if not job_id:
        return {"ok": False, "error": "job_id is required"}

    job = await session.get(MetaEvaluationJob, job_id)
    if job is None:
        return {"ok": False, "error": f"job not found: {job_id}"}
    return {"ok": True, "job": _to_dict(job)}


async def list_jobs_by_dataset(
    session: AsyncSession,
    dataset_id: str,
    page: int = 1,
    size: int = 20,
) -> dict:
    """按 dataset_id 分页列出 jobs（按 created_at DESC）。"""
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    stmt = (
        select(MetaEvaluationJob)
        .where(MetaEvaluationJob.dataset_id == dataset_id)
        .order_by(MetaEvaluationJob.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    return {
        "ok": True,
        "items": [_to_dict(j) for j in rows],
        "page": page,
        "size": size,
        "count": len(rows),
    }


# ──────────────────────── worker 专用 ────────────────────────


async def claim_next_pending(session: AsyncSession) -> dict | None:
    """原子认领下一个 pending job。

    用 `FOR UPDATE SKIP LOCKED` 跳过其它 worker 已锁定的行，避免多 worker 抢同一 job。

    Returns:
        认领到的 job dict；没有 pending 时返 None
    """
    stmt = (
        select(MetaEvaluationJob)
        .where(MetaEvaluationJob.status == "pending")
        .order_by(MetaEvaluationJob.created_at.asc())
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        return None

    # 标记 running
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(job)
    return _to_dict(job)


async def mark_running(session: AsyncSession, job_id: int, started_at: datetime) -> dict:
    """显式将 job 标为 running（一般由 claim_next_pending 自动标）。"""
    job = await session.get(MetaEvaluationJob, job_id)
    if job is None:
        return {"ok": False, "error": f"job not found: {job_id}"}
    job.status = "running"
    job.started_at = started_at
    await session.commit()
    return {"ok": True, "job_id": job_id}


async def mark_completed(
    session: AsyncSession,
    job_id: int,
    evaluation_id: int,
    *,
    elapsed_ms: int | None = None,
    token_prompt: int | None = None,
    token_completion: int | None = None,
    token_total: int | None = None,
    tool_calls_json: list[dict] | None = None,
    reasoning_log: str | None = None,
) -> dict:
    """标 job 成功完成。"""
    job = await session.get(MetaEvaluationJob, job_id)
    if job is None:
        return {"ok": False, "error": f"job not found: {job_id}"}

    job.status = "completed"
    job.evaluation_id = evaluation_id
    job.error = None
    job.elapsed_ms = elapsed_ms
    job.token_prompt = token_prompt
    job.token_completion = token_completion
    job.token_total = token_total
    job.tool_calls_json = tool_calls_json
    job.reasoning_log = reasoning_log
    job.finished_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True, "job_id": job_id}


async def mark_failed(
    session: AsyncSession,
    job_id: int,
    error: str,
    *,
    elapsed_ms: int | None = None,
    token_prompt: int | None = None,
    token_completion: int | None = None,
    token_total: int | None = None,
    tool_calls_json: list[dict] | None = None,
    reasoning_log: str | None = None,
) -> dict:
    """标 job 失败。"""
    job = await session.get(MetaEvaluationJob, job_id)
    if job is None:
        return {"ok": False, "error": f"job not found: {job_id}"}

    job.status = "failed"
    job.error = error
    job.elapsed_ms = elapsed_ms
    job.token_prompt = token_prompt
    job.token_completion = token_completion
    job.token_total = token_total
    job.tool_calls_json = tool_calls_json
    job.reasoning_log = reasoning_log
    job.finished_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True, "job_id": job_id}


async def mark_cancelled(
    session: AsyncSession,
    job_id: int,
    error: str | None = None,
    *,
    elapsed_ms: int | None = None,
) -> dict:
    """标 job 取消。"""
    job = await session.get(MetaEvaluationJob, job_id)
    if job is None:
        return {"ok": False, "error": f"job not found: {job_id}"}

    job.status = "cancelled"
    job.error = error or "cancelled by user"
    job.elapsed_ms = elapsed_ms
    job.finished_at = datetime.now(timezone.utc)
    await session.commit()
    return {"ok": True, "job_id": job_id}


async def reset_stale_running(
    session: AsyncSession,
    stale_threshold_seconds: int = 300,
) -> int:
    """把超时未结束的 running job 重置为 pending（重启兜底用）。

    判定标准：started_at IS NOT NULL AND started_at < now() - threshold。

    Returns:
        被重置的 job 数
    """
    threshold = datetime.now(timezone.utc).timestamp() - stale_threshold_seconds
    threshold_dt = datetime.fromtimestamp(threshold, tz=timezone.utc)

    stmt = (
        update(MetaEvaluationJob)
        .where(
            MetaEvaluationJob.status == "running",
            MetaEvaluationJob.started_at.is_not(None),
            MetaEvaluationJob.started_at < threshold_dt,
        )
        .values(status="pending", started_at=None)
    )
    result = await session.execute(stmt)
    await session.commit()
    return int(result.rowcount or 0)


__all__ = [
    "create_job",
    "get_job",
    "list_jobs_by_dataset",
    "claim_next_pending",
    "mark_running",
    "mark_completed",
    "mark_failed",
    "mark_cancelled",
    "reset_stale_running",
]