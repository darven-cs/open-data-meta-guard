"""数据质量评估 API 路由（v2.0 同步评估）。

路由（prefix=`/data-quality`）：
    POST   /data-quality              触发评估（同步）
    GET    /data-quality/{id}          单条详情
    GET    /data-quality               按 dataset_id 列历史
    GET    /data-quality/downloads     data_downloads + 最新 quality eval 摘要
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.resp import ResponseModel
from app.core.db import get_db
from app.dao import data_quality_evaluation as dq_dao
from app.schemas.data_quality import (
    QualityRequest,
    QualityResponse,
    QualityDetail,
    QualityListItem,
    QualityListResponse,
    DownloadWithQualityItem,
    DownloadWithQualityListResponse,
)
from app.service import data_quality as service

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


# ──────────────────────── 触发评估（同步） ────────────────────────


@router.post(
    "",
    response_model=ResponseModel,
)
async def trigger_quality_evaluation(
    body: QualityRequest,
    session: AsyncSession = Depends(get_db),
):
    """触发一次数据质量评估（同步执行，立即返回结果）。

    评估流程：
        1) 读 data_download 记录
        2) 调 quality_tool（pandas + pandera）
        3) 写 data_quality_evaluations 记录
        4) 返回 evaluation
    """
    result = await service.evaluate_data(
        session=session,
        data_download_id=body.data_download_id,
    )
    if not result.get("ok"):
        return ResponseModel.fail(code=500, msg=result.get("error", "evaluation failed"))

    ev = result["evaluation"]
    payload = QualityResponse(
        ok=True,
        evaluation_id=ev["id"],
        data_download_id=ev["data_download_id"],
        created_at=ev.get("created_at", ""),
    )
    return ResponseModel.success(payload.model_dump(), msg="数据质量评估完成")


# ──────────────────────── downloads + latest eval（必须在 /{id} 之前） ────────


@router.get(
    "/downloads",
    response_model=ResponseModel,
)
async def list_downloads_with_evaluation(
    page: int = Query(1, ge=1, description="页码（1-based）"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    session: AsyncSession = Depends(get_db),
):
    """data_downloads 列表 + 每条最新 quality eval 摘要。"""
    result = await dq_dao.list_downloads_with_latest_evaluation(
        session=session,
        page=page,
        size=size,
    )
    if not result.get("ok"):
        return ResponseModel.fail(code=500, msg=result.get("error", "list failed"))

    payload = DownloadWithQualityListResponse(
        items=[DownloadWithQualityItem(**it) for it in result["items"]],
        page=result["page"],
        size=result["size"],
        count=result["count"],
    )
    return ResponseModel.success(payload.model_dump())


# ──────────────────────── 单条详情 ────────────────────────


@router.get(
    "/{evaluation_id}",
    response_model=ResponseModel,
)
async def get_evaluation(
    evaluation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """单条 quality evaluation 详情（含 summary / issues / Markdown 报告）。"""
    res = await dq_dao.get_evaluation(
        session=session,
        evaluation_id=evaluation_id,
    )
    if not res.get("ok"):
        return ResponseModel.fail(code=404, msg=res.get("error", "evaluation not found"))

    ev = res["evaluation"]
    payload = QualityDetail(
        id=ev["id"],
        dataset_id=ev["dataset_id"],
        data_download_id=ev["data_download_id"],
        evaluation_content=ev["evaluation_content"],
        summary=ev.get("summary") or {},
        issues=ev.get("issues") or [],
        created_at=ev.get("created_at"),
    )
    return ResponseModel.success(payload.model_dump())


# ──────────────────────── 历史列表（按 dataset_id） ────────────────────────


@router.get(
    "",
    response_model=ResponseModel,
)
async def list_evaluations(
    dataset_id: str = Query(
        ...,
        min_length=64,
        max_length=64,
        description="sha256(url) 64 位 hex（必填）",
    ),
    page: int = Query(1, ge=1, description="页码（1-based）"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    session: AsyncSession = Depends(get_db),
):
    """按 dataset_id 列质量评估历史。"""
    result = await service.list_evaluations(
        session=session,
        dataset_id=dataset_id,
        page=page,
        size=size,
    )
    if not result.get("ok"):
        return ResponseModel.fail(code=500, msg=result.get("error", "list failed"))

    payload = QualityListResponse(
        items=[QualityListItem(**it) for it in result["items"]],
        page=result["page"],
        size=result["size"],
        count=result["count"],
    )
    return ResponseModel.success(payload.model_dump())
