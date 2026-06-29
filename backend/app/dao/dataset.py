"""
datasets 表 DAO — 5 个 plain async 函数。

设计要点：
- 函数签名接 Python 类型（str / int / dict），不接 ORM 对象
- 错误统一返回 `{"ok": False, "error": "..."}`；不抛业务异常
- IntegrityError → 回滚 + 错误 dict
- session 由 FastAPI Depends(get_db) 注入；事务边界由调用方控制

v2.0 简化：
- 字段名 metadata（无下划线），与 plan 一致
- 字段名 status（无 scrape_ 前缀），三态：pending / scraped / failed
- 列表/详情不再抽 title / publisher（v2.0 让前端直接展示 JSONB 折叠树）
"""
import hashlib

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.dataset import Dataset


# ──────────────────────── helpers ────────────────────────


def compute_dataset_id(url: str) -> str:
    """datasets.id = sha256(url) 64 位 hex（与 model.Dataset.id 约定一致）。"""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _to_dict(ds: Dataset) -> dict:
    """ORM → dict（序列化为 API 友好格式）。

    Python 属性 `metadata_` → JSON 字段 `metadata`（API 对外契约不带下划线）。
    """
    return {
        "id": ds.id,
        "url": ds.url,
        "metadata": ds.metadata_ or {},
        "status": ds.status,
        "has_uploaded": ds.has_uploaded,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
    }


# ──────────────────────── CRUD ────────────────────────


async def upsert_dataset(
    session: AsyncSession,
    dataset_id: str,
    url: str,
    metadata: dict,
    status: str,
) -> dict:
    """按 dataset_id 幂等 upsert。

    语义：
    - dataset_id 已存在 → 覆盖 url + metadata + status
    - 不存在 → 新建（dataset_id 由调用方按 sha256(url) 算出）

    Args:
        session: 由 Depends(get_db) 注入的 AsyncSession
        dataset_id: sha256(url) 64 位 hex
        url: 原始数据源 URL
        metadata: ScrapResult.metadata（dict）
        status: 'pending' / 'scraped' / 'failed'

    Returns:
        {"ok": True, "dataset_id": "..."}
        {"ok": False, "error": "..."}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if not url:
        return {"ok": False, "error": "url is required"}
    if not isinstance(metadata, dict):
        return {"ok": False, "error": "metadata must be dict"}
    if not status:
        return {"ok": False, "error": "status is required"}

    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        ds = Dataset(
            id=dataset_id,
            url=url,
            metadata_=metadata,
            status=status,
        )
        session.add(ds)
    else:
        ds.url = url
        ds.metadata_ = metadata
        ds.status = status

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"upsert_dataset integrity error: {e}"}
    return {"ok": True, "dataset_id": dataset_id}


async def get_dataset(
    session: AsyncSession,
    dataset_id: str,
) -> dict:
    """按 id 查 dataset 完整字段。

    Returns:
        {"ok": True, "dataset": {...}}
        {"ok": False, "error": "dataset_id is required" | "dataset not found: ..."}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}

    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        return {"ok": False, "error": f"dataset not found: {dataset_id}"}

    return {"ok": True, "dataset": _to_dict(ds)}


async def list_datasets(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
    status: str = "",
) -> dict:
    """分页 + status 过滤，按 created_at DESC。

    Args:
        page: 1-based
        size: 每页条数（1..100，超界自动夹到 20）
        status: '' 表示不过滤；否则精确匹配（pending / scraped / failed）

    Returns:
        {"ok": True, "items": [...], "page": int, "size": int, "count": int}
    """
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    stmt = select(Dataset).order_by(Dataset.created_at.desc())
    if status:
        stmt = stmt.where(Dataset.status == status)
    stmt = stmt.offset((page - 1) * size).limit(size)

    result = await session.execute(stmt)
    rows = result.scalars().all()

    return {
        "ok": True,
        "items": [_to_dict(ds) for ds in rows],
        "page": page,
        "size": size,
        "count": len(rows),
    }


async def update_dataset_metadata(
    session: AsyncSession,
    dataset_id: str,
    metadata: dict,
) -> dict:
    """整块覆盖 metadata；status 不变（保持 'scraped' / 'failed' 等业务状态）。

    Returns:
        {"ok": True, "dataset_id": "..."}
        {"ok": False, "error": "..."}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if not isinstance(metadata, dict):
        return {"ok": False, "error": "metadata must be dict"}

    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        return {"ok": False, "error": f"dataset not found: {dataset_id}"}

    ds.metadata_ = metadata

    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        return {
            "ok": False,
            "error": f"update_dataset_metadata integrity error: {e}",
        }
    return {"ok": True, "dataset_id": dataset_id}


async def delete_dataset(
    session: AsyncSession,
    dataset_id: str,
) -> dict:
    """按 id 删 dataset（幂等：不存在也返 ok=True）。

    Returns:
        {"ok": True, "dataset_id": "...", "deleted": True/False}
        {"ok": False, "error": "dataset_id is required"}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}

    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        # 幂等：不存在也算成功
        return {"ok": True, "dataset_id": dataset_id, "deleted": False}

    await session.execute(
        sa_delete(Dataset).where(Dataset.id == dataset_id)
    )
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"delete_dataset integrity error: {e}"}
    return {"ok": True, "dataset_id": dataset_id, "deleted": True}


async def set_has_uploaded(
    session: AsyncSession,
    dataset_id: str,
    flag: bool,
) -> dict:
    """翻转 dataset.has_uploaded 布尔位（Phase 3 上传/删除时用）。

    Returns:
        {"ok": True, "dataset_id": "..."}
        {"ok": False, "error": "dataset not found: ..." | ...}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}

    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        return {"ok": False, "error": f"dataset not found: {dataset_id}"}

    ds.has_uploaded = bool(flag)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"set_has_uploaded integrity error: {e}"}
    return {"ok": True, "dataset_id": dataset_id}
