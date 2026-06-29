"""数据采集（人工上传）service 层。

设计要点：
- 6 个 async 函数：upload_file / list_datasets_for_select / list_downloads
                   / get_download / delete_download / stream_download
- 路径安全：所有磁盘路径走 safe_path + safe_dataset_id
- 大小限制：双重保护（路由 Content-Length + service 字节累计）
- 写盘失败或 commit 失败：清部分文件 + 回滚 DB
"""
import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.file_storage import safe_dataset_id, safe_path
from app.core.log import logger
from app.dao import dataset as dataset_dao
from app.dao import data_download as data_download_dao
from app.model.data_download import DataDownload


# 允许的文件扩展名（小写）
_ALLOWED_EXTS: frozenset[str] = frozenset({"csv", "xlsx", "json"})

# 流式写盘分块大小（1 MiB）
_CHUNK_SIZE = 1024 * 1024


def _detect_extension(file: UploadFile) -> tuple[str, str]:
    """从 UploadFile.filename 抽取小写后缀。

    Returns:
        (ext, basename) — ext 已 lower；basename 是去掉扩展名的文件名
    """
    raw_name = file.filename or ""
    basename, dot, ext = raw_name.rpartition(".")
    if not dot or not ext:
        return "", ""
    return ext.lower(), basename


# ──────────────────────── 端点对应 service ────────────────────────


async def upload_file(
    session: AsyncSession,
    dataset_id: str,
    file: UploadFile,
) -> dict[str, Any]:
    """接收上传文件，落盘 + 算 sha256 + 落库 + 翻 has_uploaded。

    流程：
        1. 校验扩展名（小写 ∈ {csv, xlsx, json}）
        2. dataset 存在性校验
        3. 目标目录：download_dir / uploads / {safe_dataset_id}
        4. 文件名：{ms_timestamp}_{safe_basename}.{ext}
        5. shutil.copyfileobj 分块写盘 + sha256
        6. 字节累计 > settings.download_max_file_size_mb → 清部分文件 + 返 too large
        7. 空文件拒绝
        8. 单事务：insert DataDownload + set_has_uploaded True；commit 失败清盘

    Returns:
        {"ok": True, "download_id": int, "record": dict}
        {"ok": False, "error": "..."}
    """
    if not dataset_id:
        return {"ok": False, "error": "dataset_id is required"}
    if file is None:
        return {"ok": False, "error": "file is required"}

    ext, basename = _detect_extension(file)
    if not ext or ext not in _ALLOWED_EXTS:
        return {
            "ok": False,
            "error": f"unsupported file extension: {ext!r}（仅允许 csv/xlsx/json）",
        }

    # 2) dataset 存在性
    ds_res = await dataset_dao.get_dataset(session=session, dataset_id=dataset_id)
    if not ds_res.get("ok"):
        return {"ok": False, "error": "dataset not found"}

    # 3) 目标目录
    safe_ds = safe_dataset_id(dataset_id)
    try:
        target_dir = safe_path(settings.download_dir, "uploads", safe_ds)
    except ValueError as e:
        return {"ok": False, "error": f"path safety check failed: {e}"}
    target_dir.mkdir(parents=True, exist_ok=True)

    # 4) 文件名：毫秒时间戳前缀避免重名
    ms_ts = int(time.time() * 1000)
    safe_basename = safe_dataset_id(basename or "file")
    file_name = f"{ms_ts}_{safe_basename}.{ext}"
    dest_path = target_dir / file_name

    # 5) 分块写盘 + sha256 + 大小累计
    max_bytes = settings.download_max_file_size_mb * 1024 * 1024
    sha256 = hashlib.sha256()
    total = 0
    try:
        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    out.close()
                    dest_path.unlink(missing_ok=True)
                    return {
                        "ok": False,
                        "error": (
                            f"file too large (> "
                            f"{settings.download_max_file_size_mb} MB)"
                        ),
                    }
                sha256.update(chunk)
                out.write(chunk)
    except OSError as e:
        dest_path.unlink(missing_ok=True)
        logger.exception("[data-collect] write failed path={} err={}", dest_path, e)
        return {"ok": False, "error": f"failed to write file: {e}"}
    finally:
        await file.close()

    # 7) 空文件拒绝
    if total == 0:
        dest_path.unlink(missing_ok=True)
        return {"ok": False, "error": "empty file is not allowed"}

    file_sha256_hex = sha256.hexdigest()

    # 8) 单事务：insert + set_has_uploaded
    create_res = await data_download_dao.create_download(
        session=session,
        dataset_id=dataset_id,
        file_name=file.filename or file_name,
        file_path=str(dest_path),
        file_format=ext,
        file_size=total,
        file_sha256=file_sha256_hex,
    )
    if not create_res.get("ok"):
        # commit 失败 → 清盘
        dest_path.unlink(missing_ok=True)
        return {"ok": False, "error": create_res.get("error", "create_download failed")}

    flip_res = await dataset_dao.set_has_uploaded(
        session=session, dataset_id=dataset_id, flag=True
    )
    if not flip_res.get("ok"):
        # commit 失败 → 清盘 + 清刚插入的 DB 行
        dest_path.unlink(missing_ok=True)
        # best-effort 删除刚创建的记录
        try:
            await data_download_dao.delete_with_file(
                session=session, download_id=create_res["download_id"]
            )
        except Exception:
            pass
        return {"ok": False, "error": flip_res.get("error", "set_has_uploaded failed")}

    return {
        "ok": True,
        "download_id": create_res["download_id"],
        "record": create_res["record"],
    }


async def list_datasets_for_select(
    session: AsyncSession,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """分页返回 datasets 列表（含 pending），按 created_at DESC。

    Returns:
        {"ok": True, "items": [...], "page": int, "size": int, "count": int}
    """
    from sqlalchemy import func, select

    from app.model.dataset import Dataset

    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    # count
    cnt_stmt = select(func.count()).select_from(Dataset)
    cnt_res = await session.execute(cnt_stmt)
    total = cnt_res.scalar() or 0

    stmt = (
        select(Dataset)
        .order_by(Dataset.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()

    items = [
        {
            "id": ds.id,
            "url": ds.url,
            "has_uploaded": ds.has_uploaded,
            "status": ds.status,
            "created_at": ds.created_at.isoformat() if ds.created_at else None,
        }
        for ds in rows
    ]
    return {"ok": True, "items": items, "page": page, "size": size, "count": total}


async def list_downloads(
    session: AsyncSession,
    dataset_id: str,
    page: int = 1,
    size: int = 20,
) -> dict[str, Any]:
    """按 dataset_id 分页列出已上传文件。"""
    return await data_download_dao.list_by_dataset(
        session=session, dataset_id=dataset_id, page=page, size=size
    )


async def get_download(session: AsyncSession, download_id: int) -> dict[str, Any]:
    """按 id 查下载记录详情。"""
    return await data_download_dao.get_by_id(
        session=session, download_id=download_id
    )


async def delete_download(
    session: AsyncSession,
    download_id: int,
) -> dict[str, Any]:
    """删 DB 行 + 磁盘文件；dataset.has_uploaded 在删到 0 时翻回 False。"""
    # 先把目标 dataset_id 取出来（删完就没了）
    detail = await data_download_dao.get_by_id(
        session=session, download_id=download_id
    )
    if not detail.get("ok"):
        return detail
    target_dataset_id = detail["download"]["dataset_id"]

    del_res = await data_download_dao.delete_with_file(
        session=session, download_id=download_id
    )
    if not del_res.get("ok"):
        return del_res

    # 检查该 dataset 还剩几条 upload；剩 0 条则翻 has_uploaded 回 False
    from sqlalchemy import func, select

    from app.model.data_download import DataDownload as _DD

    count_stmt = (
        select(func.count())
        .select_from(_DD)
        .where(_DD.dataset_id == target_dataset_id)
    )
    count_res = await session.execute(count_stmt)
    remaining = int(count_res.scalar() or 0)
    if remaining == 0:
        flip_res = await dataset_dao.set_has_uploaded(
            session=session, dataset_id=target_dataset_id, flag=False
        )
        if not flip_res.get("ok"):
            # 翻位失败不回滚删除（DB 行已删，仅标记位遗留 True）
            logger.warning(
                "[data-collect] set_has_uploaded(False) failed: {}",
                flip_res.get("error"),
            )

    return {"ok": True, "download_id": download_id, "deleted": True}


async def stream_download(
    session: AsyncSession,
    download_id: int,
) -> tuple[Path, str] | dict:
    """返回 (磁盘路径, 文件名) 元组（成功）或 {ok: False} dict（失败）。

    给 FileResponse 直接消费。
    """
    res = await data_download_dao.get_disk_path(
        session=session, download_id=download_id
    )
    if not res.get("ok"):
        return res
    path = Path(res["file_path"])
    if not path.is_file():
        return {"ok": False, "error": f"file missing on disk: {path}"}
    return path, res["file_name"]


__all__ = [
    "upload_file",
    "list_datasets_for_select",
    "list_downloads",
    "get_download",
    "delete_download",
    "stream_download",
]