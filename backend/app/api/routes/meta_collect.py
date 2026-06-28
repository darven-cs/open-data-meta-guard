"""
元数据采集 API 路由（v2.0 Phase 1）。

路由（prefix=`/meta-collect`，单一职责）：
    POST   /datasets/ingest                同步批量采集（多 URL）
    GET    /datasets                       datasets 分页列表
    GET    /datasets/{dataset_id}          单 dataset 详情
    PUT    /datasets/{dataset_id}          整块覆盖 metadata
    DELETE /datasets/{dataset_id}          删 dataset（幂等）

设计：
- CRUD 对象是 datasets 表（操作 metadata JSONB）
- URL 校验在路由层做（FastAPI Depends），避免 service 接到非法输入
- ingest 走 service.ingest_urls 同步阻塞；不走 SSE/后台任务
"""
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.resp import ResponseModel
from app.core.db import get_db
from app.dao import dataset as dataset_dao
from app.schemas.meta_collect import (
    DatasetDetailResponse,
    DatasetListItem,
    DatasetListResponse,
    IngestRequest,
    IngestResponse,
    IngestItem,
    UpdateRequest,
)
from app.service import meta_collect as service


router = APIRouter(prefix="/meta-collect")


# ──────────────────────── helpers ────────────────────────


def _dedup_and_validate_urls(urls: list[str]) -> list[str]:
    """去重 + scheme + 长度校验。

    与 v1.0 路由层同语义；service 层不做 4xx 校验，由路由守门。
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in urls:
        u = (raw or "").strip()
        if not u:
            continue
        if len(u) > 2048:
            raise HTTPException(
                status_code=400,
                detail=f"URL 过长（>{2048} 字符）: {u[:80]}...",
            )
        parsed = urlparse(u)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HTTPException(
                status_code=400,
                detail=f"URL 必须以 http/https 开头且含 host: {u}",
            )
        if u not in seen:
            seen.add(u)
            out.append(u)
    if not out:
        raise HTTPException(status_code=400, detail="urls 不能全为空")
    return out


# ──────────────────────── 端点 ────────────────────────


@router.post(
    "/datasets/ingest",
    response_model=ResponseModel,
)
async def ingest_datasets(
    body: IngestRequest,
    session: AsyncSession = Depends(get_db),
):
    """同步批量采集（v2.0 简化：不等后台、不走 SSE）。

    流程：
        1. 校验 URL（_dedup_and_validate_urls）
        2. service.ingest_urls 同步遍历逐个抓取
        3. 返回 items 数组 + success_count / failed_count
    """
    urls = _dedup_and_validate_urls(body.urls)
    result = await service.ingest_urls(session=session, urls=urls)
    payload = IngestResponse(
        ok=result["ok"],
        items=[IngestItem(**it) for it in result["items"]],
        success_count=result["success_count"],
        failed_count=result["failed_count"],
    )
    return ResponseModel.success(
        payload.model_dump(),
        msg=f"采集完成：{payload.success_count}/{len(urls)} 成功",
    )


@router.get(
    "/datasets",
    response_model=ResponseModel,
)
async def list_datasets(
    page: int = Query(1, ge=1, description="页码（1-based）"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    status: Optional[str] = Query(
        None,
        description="按 status 过滤（pending / scraped / failed）",
    ),
    session: AsyncSession = Depends(get_db),
):
    """datasets 分页列表（按 created_at DESC；可按 status 过滤）。"""
    result = await dataset_dao.list_datasets(
        session=session,
        page=page,
        size=size,
        status=status or "",
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "list_datasets failed"),
        )

    payload = DatasetListResponse(
        items=[DatasetListItem(**it) for it in result["items"]],
        page=result["page"],
        size=result["size"],
        count=result["count"],
    )
    return ResponseModel.success(payload.model_dump())


@router.get(
    "/datasets/{dataset_id}",
    response_model=ResponseModel,
)
async def get_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_db),
):
    """单 dataset 详情。"""
    result = await dataset_dao.get_dataset(session=session, dataset_id=dataset_id)
    if not result.get("ok"):
        # 404 比 500 更准
        raise HTTPException(
            status_code=404,
            detail=result.get("error", "dataset not found"),
        )

    ds = result["dataset"]
    payload = DatasetDetailResponse(**ds)
    return ResponseModel.success(payload.model_dump())


@router.put(
    "/datasets/{dataset_id}",
    response_model=ResponseModel,
)
async def update_dataset(
    dataset_id: str,
    body: UpdateRequest,
    session: AsyncSession = Depends(get_db),
):
    """整块覆盖 metadata；status 保持不变（由后端管控）。"""
    result = await dataset_dao.update_dataset_metadata(
        session=session,
        dataset_id=dataset_id,
        metadata=body.metadata,
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=404,
            detail=result.get("error", "update failed"),
        )

    # 回读详情返回（前端可直接刷新 drawer）
    detail_res = await dataset_dao.get_dataset(session=session, dataset_id=dataset_id)
    ds = detail_res["dataset"]
    payload = DatasetDetailResponse(**ds)
    return ResponseModel.success(payload.model_dump(), msg="metadata 已更新")


@router.delete(
    "/datasets/{dataset_id}",
    response_model=ResponseModel,
)
async def delete_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_db),
):
    """删 dataset（幂等：不存在也返 ok）。"""
    result = await dataset_dao.delete_dataset(
        session=session,
        dataset_id=dataset_id,
    )
    if not result.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "delete_dataset failed"),
        )

    msg = "dataset 已删除" if result.get("deleted") else "dataset 不存在（幂等成功）"
    return ResponseModel.success(
        {
            "dataset_id": dataset_id,
            "deleted": result.get("deleted", False),
        },
        msg=msg,
    )
