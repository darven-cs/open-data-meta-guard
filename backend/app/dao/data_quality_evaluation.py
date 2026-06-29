"""data_quality_evaluations 表 DAO。

设计要点：
- 函数签名接 Python 类型，不接 ORM 对象
- 错误统一返回 `{"ok": False, "error": "..."}`
- session.commit() 在 DAO 内显式调用
"""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.data_download import DataDownload
from app.model.data_quality_evaluation import DataQualityEvaluation


# ──────────────────────── helpers ────────────────────────


def _to_dict(ev: DataQualityEvaluation) -> dict[str, Any]:
    return {
        "id": ev.id,
        "dataset_id": ev.dataset_id,
        "data_download_id": ev.data_download_id,
        "evaluation_content": ev.evaluation_content,
        "summary": ev.summary or {},
        "issues": ev.issues or [],
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


def _download_to_dict(d: DataDownload) -> dict[str, Any]:
    return {
        "id": d.id,
        "dataset_id": d.dataset_id,
        "file_name": d.file_name,
        "file_path": d.file_path,
        "file_format": d.file_format,
        "file_size": d.file_size,
        "file_sha256": d.file_sha256,
        "source": d.source,
        "status": d.status,
        "error_message": d.error_message,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


# ──────────────────────── CRUD ────────────────────────


async def create_evaluation(
    session: AsyncSession,
    dataset_id: str,
    data_download_id: int,
    evaluation_content: str,
    summary: dict,
    issues: list,
) -> dict:
    """新建一条 quality evaluation 记录。

    Returns:
        {"ok": True, "evaluation_id": int}
        {"ok": False, "error": "..."}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if not data_download_id:
        return {"ok": False, "error": "data_download_id is required"}
    if not evaluation_content:
        return {"ok": False, "error": "evaluation_content is required"}

    ev = DataQualityEvaluation(
        dataset_id=dataset_id,
        data_download_id=data_download_id,
        evaluation_content=evaluation_content,
        summary=summary or {},
        issues=issues or [],
    )
    session.add(ev)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"create_evaluation integrity error: {e}"}

    await session.refresh(ev)
    return {"ok": True, "evaluation_id": ev.id}


async def get_evaluation(
    session: AsyncSession,
    evaluation_id: int,
) -> dict:
    """按 id 查 evaluation 完整字段。

    Returns:
        {"ok": True, "evaluation": {...}}
        {"ok": False, "error": "..."}
    """
    if not evaluation_id:
        return {"ok": False, "error": "evaluation_id is required"}

    ev = await session.get(DataQualityEvaluation, evaluation_id)
    if ev is None:
        return {"ok": False, "error": f"evaluation not found: {evaluation_id}"}

    return {"ok": True, "evaluation": _to_dict(ev)}


async def list_evaluations(
    session: AsyncSession,
    dataset_id: str,
    page: int = 1,
    size: int = 20,
) -> dict:
    """按 dataset_id 分页，按 created_at DESC。

    Returns:
        {"ok": True, "items": [...], "page": int, "size": int, "count": int}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    stmt = (
        select(DataQualityEvaluation)
        .where(DataQualityEvaluation.dataset_id == dataset_id)
        .order_by(DataQualityEvaluation.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    return {
        "ok": True,
        "items": [_to_dict(ev) for ev in rows],
        "page": page,
        "size": size,
        "count": len(rows),
    }


async def list_downloads_with_latest_evaluation(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> dict:
    """data_downloads 分页列表 + 每条最新 quality eval 摘要。

    实现：
        1) 分页查 data_downloads（按 created_at DESC）
        2) window function 一次查所有 data_download_id 的最新 evaluation
        3) 拼装 items

    Returns:
        {"ok": True, "items": [...], "page": int, "size": int, "count": int}
    """
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    # 1) data_downloads 分页
    dl_stmt = (
        select(DataDownload)
        .order_by(DataDownload.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    dl_result = await session.execute(dl_stmt)
    downloads = dl_result.scalars().all()

    if not downloads:
        return {"ok": True, "items": [], "page": page, "size": size, "count": 0}

    dl_ids = [d.id for d in downloads]

    # 2) window function: 最新 evaluation
    rn_col = func.row_number().over(
        partition_by=DataQualityEvaluation.data_download_id,
        order_by=DataQualityEvaluation.created_at.desc(),
    ).label("rn")

    eval_inner = (
        select(
            DataQualityEvaluation.data_download_id,
            DataQualityEvaluation.id,
            DataQualityEvaluation.summary,
            DataQualityEvaluation.created_at,
            rn_col,
        )
        .where(DataQualityEvaluation.data_download_id.in_(dl_ids))
        .subquery()
    )

    eval_stmt = select(
        eval_inner.c.data_download_id,
        eval_inner.c.id,
        eval_inner.c.summary,
        eval_inner.c.created_at,
    ).where(eval_inner.c.rn == 1)

    eval_result = await session.execute(eval_stmt)
    eval_map: dict[int, dict[str, Any]] = {}
    for row in eval_result:
        eval_map[row.data_download_id] = {
            "id": row.id,
            "summary": row.summary or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    # 3) 拼装
    items: list[dict[str, Any]] = []
    for d in downloads:
        dl_dict = _download_to_dict(d)
        dl_dict["latest_evaluation"] = eval_map.get(d.id)
        items.append(dl_dict)

    return {
        "ok": True,
        "items": items,
        "page": page,
        "size": size,
        "count": len(items),
    }
