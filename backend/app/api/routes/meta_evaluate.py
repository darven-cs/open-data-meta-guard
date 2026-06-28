"""元数据评估 API 路由（v2.0 Phase 2）。

路由（prefix=`/meta-evaluate`，RESTful）：
    POST  /evaluations                触发评估（body: {dataset_id}）
    GET   /evaluations/{evaluation_id} 单条详情
    GET   /evaluations                历史列表（按 dataset_id 过滤 + 分页）

设计：
- 同步阻塞：评估一次 30-60s（agent 调 3 个 observation tool）
- 失败统一用 ResponseModel.fail 包（路由层只把 ok=False 转 4xx/5xx）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.resp import ResponseModel
from app.core.db import get_db
from app.dao import meta_evaluation as meta_eval_dao
from app.schemas.meta_evaluate import (
    DatasetEvalItem,
    DatasetEvalListResponse,
    EvaluateRequest,
    EvaluateResponse,
    EvaluationDetail,
    EvaluationListItem,
    EvaluationListResponse,
)
from app.service import meta_evaluate as service


router = APIRouter(prefix="/meta-evaluate", tags=["meta-evaluate"])


# ──────────────────────── 端点 ────────────────────────


@router.post(
    "/evaluations",
    response_model=ResponseModel,
)
async def trigger_evaluate(
    body: EvaluateRequest,
    session: AsyncSession = Depends(get_db),
):
    """触发一次元数据评估（同步阻塞 30-60s）。

    流程：
        1. service.evaluate_dataset 调 agent + 落库 + 生成 Markdown 报告
        2. dataset 不存在 → 404
        3. agent 异常 → 500
    """
    result = await service.evaluate_dataset(
        session=session,
        dataset_id=body.dataset_id,
    )
    if not result.get("ok"):
        err = result.get("error", "evaluate_dataset failed")
        # dataset not found 用 404；agent 失败 / 其他用 500
        code = 404 if "dataset not found" in err else 500
        return ResponseModel.fail(code=code, msg=err)

    payload = EvaluateResponse(
        ok=True,
        evaluation_id=result["evaluation_id"],
        dataset_id=result["dataset_id"],
        score_total=result["score_total"],
        grade=result["grade"],
        created_at=result["created_at"],
    )
    return ResponseModel.success(
        payload.model_dump(),
        msg=f"评估完成：{payload.grade} / {payload.score_total}/405",
    )


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=ResponseModel,
)
async def get_evaluation(
    evaluation_id: int,
    session: AsyncSession = Depends(get_db),
):
    """单条 evaluation 详情（含 5 维分 + rule_scores + Markdown 报告）。"""
    result = await meta_eval_dao.get_evaluation(
        session=session,
        evaluation_id=evaluation_id,
    )
    if not result.get("ok"):
        return ResponseModel.fail(
            code=404,
            msg=result.get("error", "evaluation not found"),
        )

    ev = result["evaluation"]
    payload = EvaluationDetail(
        id=ev["id"],
        dataset_id=ev["dataset_id"],
        score_total=ev["score_total"],
        score_discover=ev["score_discover"],
        score_access=ev["score_access"],
        score_interop=ev["score_interop"],
        score_reuse=ev["score_reuse"],
        score_context=ev["score_context"],
        grade=ev["grade"],
        rule_scores=ev.get("rule_scores") or {},
        llm_notes=ev.get("llm_notes") or {},
        evaluation_content=ev["evaluation_content"],
        report_json=ev.get("report_json"),
        created_at=ev.get("created_at"),
    )
    return ResponseModel.success(payload.model_dump())


@router.get(
    "/evaluations",
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
    grade: str = Query(
        "",
        description="按 grade 过滤（Excellent / Good / Sufficient / Bad）；空表示不过滤",
    ),
    session: AsyncSession = Depends(get_db),
):
    """按 dataset_id 拉评估历史 + 可选 grade 过滤 + 分页。"""
    result = await service.list_evaluations(
        session=session,
        dataset_id=dataset_id,
        page=page,
        size=size,
        grade=grade,
    )
    if not result.get("ok"):
        return ResponseModel.fail(
            code=500,
            msg=result.get("error", "list_evaluations failed"),
        )

    payload = EvaluationListResponse(
        items=[EvaluationListItem(**it) for it in result["items"]],
        page=result["page"],
        size=result["size"],
        count=result["count"],
    )
    return ResponseModel.success(payload.model_dump())


@router.get(
    "/datasets",
    response_model=ResponseModel,
)
async def list_datasets_with_evaluation(
    page: int = Query(1, ge=1, description="页码（1-based）"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    status: str = Query(
        "",
        description="按 status 过滤（pending / scraped / failed）；空表示不过滤",
    ),
    session: AsyncSession = Depends(get_db),
):
    """datasets 列表 + 每条 dataset 的最新 evaluation 摘要。

    评估页直接展示这个列表 + 行级「触发评估 / 查看评估」按钮。
    """
    result = await meta_eval_dao.list_datasets_with_latest_evaluation(
        session=session,
        page=page,
        size=size,
        status=status,
    )
    if not result.get("ok"):
        return ResponseModel.fail(
            code=500,
            msg=result.get("error", "list_datasets_with_latest_evaluation failed"),
        )

    payload = DatasetEvalListResponse(
        items=[DatasetEvalItem(**it) for it in result["items"]],
        page=result["page"],
        size=result["size"],
        count=result["count"],
    )
    return ResponseModel.success(payload.model_dump())