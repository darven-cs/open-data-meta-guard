"""数据采集 API 路由。

路由（prefix=`/data-collect`）：
    GET    /data-collect/datasets                分页 datasets 列表（按 dataset 维度）
    POST   /data-collect/upload                  multipart 上传
    GET    /data-collect/                        列表（?dataset_id&page&size）
    GET    /data-collect/{id}                    详情
    DELETE /data-collect/{id}                    删行 + 文件
    GET    /data-collect/{id}/download          FileResponse 流式下载

设计：
- 路由层做大小上限 Content-Length 预检（早返 413）
- service 层做字节累计越界清盘（兜底）
- 错误统一映射：{ok: False} → HTTPException(400/404/413)
"""
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.resp import ResponseModel
from app.core.config import settings
from app.core.db import get_db
from app.schemas.data_collect import (
    DatasetSelectItem,
    DatasetSelectListResponse,
    DownloadDetailResponse,
    DownloadListItem,
    DownloadListResponse,
    UploadResponse,
)
from app.service import data_collect as service


router = APIRouter(prefix="/data-collect")


# ──────────────────────── 错误映射 helpers ────────────────────────


def _http_from_service(res: dict, not_found_status: int = 404) -> HTTPException:
    """service {ok: False} → HTTPException。

    通过错误前缀粗略分类：
        "dataset not found" → 404
        "unsupported file extension" / "empty file" / "file too large" → 400
        "file too large" 是 service 层命中（> settings） → 413
        其他 → 500
    """
    err = (res.get("error") or "service failed").lower()
    if "not found" in err:
        return HTTPException(status_code=not_found_status, detail=res.get("error"))
    if "too large" in err:
        return HTTPException(status_code=413, detail=res.get("error"))
    if (
        "unsupported" in err
        or "empty" in err
        or "required" in err
        or "extension" in err
    ):
        return HTTPException(status_code=400, detail=res.get("error"))
    return HTTPException(status_code=500, detail=res.get("error"))


# ──────────────────────── 端点 ────────────────────────


@router.get("/datasets", response_model=ResponseModel)
async def list_datasets_for_select(
    page: int = Query(1, ge=1, description="页码（1-based）"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    session: AsyncSession = Depends(get_db),
):
    """分页返回 datasets 列表（按 dataset 维度，含 upload 状态）。"""
    res = await service.list_datasets_for_select(
        session=session, page=page, size=size
    )
    if not res.get("ok"):
        raise _http_from_service(res)
    payload = DatasetSelectListResponse(
        items=[DatasetSelectItem(**it) for it in res["items"]],
        page=res["page"],
        size=res["size"],
        count=res["count"],
    )
    return ResponseModel.success(payload.model_dump())


@router.post("/upload", response_model=ResponseModel)
async def upload_file(
    request: Request,
    dataset_id: str = Form(..., min_length=1, description="sha256(url) 64 位 hex"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
):
    """multipart 上传：dataset_id + file。

    路由层先按 Content-Length 预检（413 早返），service 层再字节累计兜底。
    """
    # 早返 413：Content-Length 超出 settings 限制
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            cl = int(content_length)
        except ValueError:
            cl = -1
        max_bytes = settings.download_max_file_size_mb * 1024 * 1024
        if cl > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"file too large (> {settings.download_max_file_size_mb} MB)"
                ),
            )

    res = await service.upload_file(
        session=session, dataset_id=dataset_id, file=file
    )
    if not res.get("ok"):
        raise _http_from_service(res)

    record = res["record"]
    payload = UploadResponse(
        download_id=record["id"],
        dataset_id=record["dataset_id"],
        file_name=record["file_name"],
        file_format=record["file_format"],
        file_size=record["file_size"],
        file_sha256=record["file_sha256"],
        created_at=record["created_at"],
    )
    return ResponseModel.success(payload.model_dump(), msg="上传成功")


@router.get("", response_model=ResponseModel)
async def list_downloads(
    dataset_id: str = Query(..., min_length=1, description="sha256(url) 64 位 hex"),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    session: AsyncSession = Depends(get_db),
):
    """按 dataset_id 分页列出已上传文件。"""
    res = await service.list_downloads(
        session=session, dataset_id=dataset_id, page=page, size=size
    )
    if not res.get("ok"):
        raise _http_from_service(res)
    payload = DownloadListResponse(
        items=[DownloadListItem(**it) for it in res["items"]],
        page=res["page"],
        size=res["size"],
        count=res["count"],
    )
    return ResponseModel.success(payload.model_dump())


@router.get("/{download_id}", response_model=ResponseModel)
async def get_download(
    download_id: int,
    session: AsyncSession = Depends(get_db),
):
    """单条 download 详情。"""
    res = await service.get_download(session=session, download_id=download_id)
    if not res.get("ok"):
        raise _http_from_service(res)
    payload = DownloadDetailResponse(**res["download"])
    return ResponseModel.success(payload.model_dump())


@router.delete("/{download_id}", response_model=ResponseModel)
async def delete_download(
    download_id: int,
    session: AsyncSession = Depends(get_db),
):
    """删行 + 磁盘文件；dataset.has_uploaded 在剩 0 条时翻回 False。"""
    res = await service.delete_download(
        session=session, download_id=download_id
    )
    if not res.get("ok"):
        raise _http_from_service(res)
    return ResponseModel.success(
        {"download_id": download_id, "deleted": True},
        msg="已删除",
    )


@router.get("/{download_id}/download")
async def download_file(
    download_id: int,
    session: AsyncSession = Depends(get_db),
):
    """FileResponse 流式下载。"""
    res = await service.stream_download(
        session=session, download_id=download_id
    )
    if isinstance(res, dict) and not res.get("ok"):
        raise _http_from_service(res)
    path, filename = res  # type: ignore[misc]
    return FileResponse(
        path=str(path),
        filename=filename,
        media_type="application/octet-stream",
    )