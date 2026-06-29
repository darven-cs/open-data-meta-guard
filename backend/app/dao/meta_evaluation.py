"""meta_evaluations 表 DAO — 5 个 plain async 函数。

设计要点：
- 函数签名接 Python 类型（str / int / dict），不接 ORM 对象
- 错误统一返回 `{"ok": False, "error": "..."}`；不抛业务异常
- session.commit() 在 DAO 内显式调用
- JSONB 列读出来就是 dict；datetime 转 ISO string
"""
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao import dataset as dataset_dao
from app.model.dataset import Dataset
from app.model.meta_evaluation import MetaEvaluation


# ──────────────────────── helpers ────────────────────────


def _to_dict(ev: MetaEvaluation) -> dict[str, Any]:
    """ORM → dict（序列化为 API 友好格式）。

    JSONB 列在 SQLAlchemy 中读出来就是 dict；datetime 转 ISO string。
    id 强转 str 以兼容 PG column type 与 ORM 类型声明不一致的过渡期。
    """
    return {
        "id": str(ev.id) if ev.id is not None else None,
        "dataset_id": ev.dataset_id,
        "score_total": ev.score_total,
        "score_discover": ev.score_discover,
        "score_access": ev.score_access,
        "score_interop": ev.score_interop,
        "score_reuse": ev.score_reuse,
        "score_context": ev.score_context,
        "grade": ev.grade,
        "rule_scores": ev.rule_scores or {},
        "llm_notes": ev.llm_notes or {},
        "evaluation_content": ev.evaluation_content,
        "report_json": ev.report_json,
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


# ──────────────────────── CRUD ────────────────────────


async def create_evaluation(
    session: AsyncSession,
    evaluation_id: str,
    dataset_id: str,
    score_total: int,
    score_discover: int,
    score_access: int,
    score_interop: int,
    score_reuse: int,
    score_context: int,
    grade: str,
    rule_scores: dict,
    llm_notes: dict,
    evaluation_content: str,
    report_json: dict | None,
) -> dict:
    """新建一条 evaluation 记录。

    Args:
        session: 由 Depends(get_db) 注入
        evaluation_id: 外部预分配的 UUID 字符串
        其余 11 个字段对齐 meta_evaluations 表

    Returns:
        {"ok": True, "evaluation_id": str}
        {"ok": False, "error": "..."}
    """
    if not evaluation_id:
        return {"ok": False, "error": "evaluation_id is required"}
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if not grade:
        return {"ok": False, "error": "grade is required"}
    if not evaluation_content:
        return {"ok": False, "error": "evaluation_content is required"}

    ev = MetaEvaluation(
        id=evaluation_id,
        dataset_id=dataset_id,
        score_total=score_total,
        score_discover=score_discover,
        score_access=score_access,
        score_interop=score_interop,
        score_reuse=score_reuse,
        score_context=score_context,
        grade=grade,
        rule_scores=rule_scores or {},
        llm_notes=llm_notes or {},
        evaluation_content=evaluation_content,
        report_json=report_json,
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
    evaluation_id: str,
) -> dict:
    """按 id 查 evaluation 完整字段。

    Returns:
        {"ok": True, "evaluation": {...}}
        {"ok": False, "error": "evaluation_id is required" | "evaluation not found: ..."}
    """
    if not evaluation_id:
        return {"ok": False, "error": "evaluation_id is required"}

    ev = await session.get(MetaEvaluation, evaluation_id)
    if ev is None:
        return {"ok": False, "error": f"evaluation not found: {evaluation_id}"}

    return {"ok": True, "evaluation": _to_dict(ev)}


async def list_evaluations(
    session: AsyncSession,
    dataset_id: str,
    page: int = 1,
    size: int = 20,
    grade: str = "",
) -> dict:
    """按 dataset_id 分页 + 可选 grade 过滤，按 created_at DESC。

    Args:
        page: 1-based
        size: 1..100（超界夹到 20）
        grade: '' 不过滤；否则精确匹配

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
        select(MetaEvaluation)
        .where(MetaEvaluation.dataset_id == dataset_id)
        .order_by(MetaEvaluation.created_at.desc())
    )
    if grade:
        stmt = stmt.where(MetaEvaluation.grade == grade)
    stmt = stmt.offset((page - 1) * size).limit(size)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    return {
        "ok": True,
        "items": [_to_dict(ev) for ev in rows],
        "page": page,
        "size": size,
        "count": len(rows),
    }


async def count_evaluations(
    session: AsyncSession,
    dataset_id: str,
) -> int:
    """按 dataset_id 统计 evaluation 总条数（分页 / 卡片用）。"""
    if not dataset_id:
        return 0
    stmt = select(func.count(MetaEvaluation.id)).where(
        MetaEvaluation.dataset_id == dataset_id
    )
    result = await session.execute(stmt)
    return int(result.scalar() or 0)


async def list_datasets_with_latest_evaluation(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
    status: str = "",
) -> dict:
    """datasets 分页列表 + 每条 dataset 的最新一次 evaluation（如有）。

    用于元数据评估页：直接展示 datasets 列表，每行带评估状态 + 触发按钮。

    实现：
        1) 先按 status 过滤分页查 datasets（按 created_at DESC）
        2) 用 window function (row_number) 一次查所有 dataset_id 的最新 evaluation
        3) 拼装成 items，latest_evaluation=None 表示未评估

    Args:
        page: 1-based
        size: 1..100（超界夹到 20）
        status: '' 不过滤；否则精确匹配

    Returns:
        {"ok": True, "items": [...], "page": int, "size": int, "count": int}
    """
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    # 1) datasets 分页
    ds_stmt = select(Dataset).order_by(Dataset.created_at.desc())
    if status:
        ds_stmt = ds_stmt.where(Dataset.status == status)
    ds_stmt = ds_stmt.offset((page - 1) * size).limit(size)

    ds_result = await session.execute(ds_stmt)
    datasets = ds_result.scalars().all()

    if not datasets:
        return {"ok": True, "items": [], "page": page, "size": size, "count": 0}

    dataset_ids = [d.id for d in datasets]

    # 2) window function: 一次查所有 dataset 的最新 evaluation
    rn_col = func.row_number().over(
        partition_by=MetaEvaluation.dataset_id,
        order_by=MetaEvaluation.created_at.desc(),
    ).label("rn")

    eval_inner = select(
        MetaEvaluation.dataset_id,
        MetaEvaluation.id,
        MetaEvaluation.score_total,
        MetaEvaluation.grade,
        MetaEvaluation.created_at,
        rn_col,
    ).where(MetaEvaluation.dataset_id.in_(dataset_ids)).subquery()

    eval_stmt = select(
        eval_inner.c.dataset_id,
        eval_inner.c.id,
        eval_inner.c.score_total,
        eval_inner.c.grade,
        eval_inner.c.created_at,
    ).where(eval_inner.c.rn == 1)

    eval_result = await session.execute(eval_stmt)
    eval_map: dict[str, dict[str, Any]] = {}
    for row in eval_result:
        eval_map[row.dataset_id] = {
            "id": str(row.id) if row.id is not None else None,
            "score_total": row.score_total,
            "grade": row.grade,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    # 3) 拼装
    items: list[dict[str, Any]] = []
    for d in datasets:
        ds_dict = dataset_dao._to_dict(d)
        ds_dict["latest_evaluation"] = eval_map.get(d.id)
        items.append(ds_dict)

    return {
        "ok": True,
        "items": items,
        "page": page,
        "size": size,
        "count": len(items),
    }