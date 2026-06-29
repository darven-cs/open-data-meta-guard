"""data_downloads 表 DAO。

设计要点：
- 函数签名接 Python 类型（str / int），不接 ORM 对象
- 错误统一返回 `{"ok": False, "error": "..."}`；不抛业务异常
- session.commit() 在 DAO 内显式调用
- delete_with_file 先删 DB 再清磁盘（DB 优先，避免脏文件无主）
"""
from pathlib import Path
from typing import Any

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import logger
from app.model.data_download import DataDownload


# ──────────────────────── helpers ────────────────────────


def _to_dict(d: DataDownload) -> dict[str, Any]:
    """ORM → dict（API 友好格式）。"""
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


async def create_download(
    session: AsyncSession,
    dataset_id: str,
    file_name: str,
    file_path: str,
    file_format: str,
    file_size: int,
    file_sha256: str,
    source: str = "user_upload",
    status: str = "uploaded",
    error_message: str | None = None,
) -> dict:
    """插入一条 data_downloads 记录。

    Returns:
        {"ok": True, "download_id": int, "record": dict}
        {"ok": False, "error": "..."}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if not file_name:
        return {"ok": False, "error": "file_name is required"}
    if not file_path:
        return {"ok": False, "error": "file_path is required"}
    if not file_format:
        return {"ok": False, "error": "file_format is required"}
    if file_size is None or file_size < 0:
        return {"ok": False, "error": "file_size is required"}
    if not file_sha256:
        return {"ok": False, "error": "file_sha256 is required"}

    row = DataDownload(
        dataset_id=dataset_id,
        file_name=file_name,
        file_path=file_path,
        file_format=file_format,
        file_size=file_size,
        file_sha256=file_sha256,
        source=source,
        status=status,
        error_message=error_message,
    )
    session.add(row)
    try:
        await session.commit()
        await session.refresh(row)
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"create_download integrity error: {e}"}
    return {
        "ok": True,
        "download_id": row.id,
        "record": _to_dict(row),
    }


async def get_by_id(session: AsyncSession, download_id: int) -> dict:
    """按 id 查记录。"""
    if not download_id:
        return {"ok": False, "error": "download_id is required"}

    row = await session.get(DataDownload, download_id)
    if row is None:
        return {"ok": False, "error": f"download not found: {download_id}"}
    return {"ok": True, "download": _to_dict(row)}


async def list_by_dataset(
    session: AsyncSession,
    dataset_id: str,
    page: int = 1,
    size: int = 20,
) -> dict:
    """按 dataset_id 分页列出（按 created_at DESC）。"""
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    stmt = (
        select(DataDownload)
        .where(DataDownload.dataset_id == dataset_id)
        .order_by(DataDownload.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    return {
        "ok": True,
        "items": [_to_dict(r) for r in rows],
        "page": page,
        "size": size,
        "count": len(rows),
    }


async def get_disk_path(session: AsyncSession, download_id: int) -> dict:
    """只取 file_path（流式下载用，避免把整行 dict 传给 FileResponse）。"""
    if not download_id:
        return {"ok": False, "error": "download_id is required"}

    row = await session.get(DataDownload, download_id)
    if row is None:
        return {"ok": False, "error": f"download not found: {download_id}"}
    return {
        "ok": True,
        "file_path": row.file_path,
        "file_name": row.file_name,
        "file_format": row.file_format,
        "file_size": row.file_size,
    }


async def delete_with_file(session: AsyncSession, download_id: int) -> dict:
    """先删 DB 行（commit），再删磁盘文件。

    Returns:
        {"ok": True, "download_id": int, "deleted": bool}
        {"ok": False, "error": "..."}
    """
    if not download_id:
        return {"ok": False, "error": "download_id is required"}

    row = await session.get(DataDownload, download_id)
    if row is None:
        return {"ok": False, "error": f"download not found: {download_id}"}

    file_path = row.file_path
    await session.execute(
        sa_delete(DataDownload).where(DataDownload.id == download_id)
    )
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"delete_with_file integrity error: {e}"}

    # DB 提交后再清磁盘（DB 优先）
    try:
        Path(file_path).unlink(missing_ok=True)
    except OSError as e:
        # 文件不存在或权限问题不阻塞：DB 已删，磁盘孤儿留待清理
        logger.warning("[data_download] failed to unlink file={} err={}", file_path, e)

    return {"ok": True, "download_id": download_id, "deleted": True}


__all__ = [
    "create_download",
    "get_by_id",
    "list_by_dataset",
    "get_disk_path",
    "delete_with_file",
]