"""元数据评估 API 路由（v2.0 async + tracing）。

路由（prefix=`/meta-evaluate`）：
    POST   /evaluations                 触发评估（202 立即返 job_id）
    GET    /evaluations/jobs/{job_id}    查 job 状态
    DELETE /evaluations/jobs/{job_id}    取消运行中的 job
    GET    /evaluations/by-job/{job_id}  job 完成后拿 evaluation 详情
    GET    /evaluations/{evaluation_id}  单条 evaluation 详情（兼容）
    GET    /evaluations                  历史评估列表（兼容）
    GET    /datasets                     datasets + 最新 evaluation 摘要（兼容）
    GET    /jobs                         按 dataset_id 拉 jobs（可选）
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.resp import ResponseModel
from app.core.db import get_db
from app.dao import meta_evaluation as meta_eval_dao
from app.dao import meta_evaluation_job as job_dao
from app.schemas.meta_evaluate import (
    DatasetEvalItem,
    DatasetEvalListResponse,
    EvaluateJobResponse,
    EvaluateRequest,
    EvaluationDetail,
    EvaluationListItem,
    EvaluationListResponse,
    JobListItem,
    JobListResponse,
)
from app.service import meta_evaluate as service
from app.workers import worker


router = APIRouter(prefix="/meta-evaluate", tags=["meta-evaluate"])


# ──────────────────────── helpers ────────────────────────


def _job_dict_to_response(d: dict) -> EvaluateJobResponse:
    return EvaluateJobResponse(
        job_id=d["id"],
        dataset_id=d["dataset_id"],
        status=d["status"],
        evaluation_id=d.get("evaluation_id"),
        error=d.get("error"),
        elapsed_ms=d.get("elapsed_ms"),
        token_prompt=d.get("token_prompt"),
        token_completion=d.get("token_completion"),
        token_total=d.get("token_total"),
        created_at=d.get("created_at"),
        started_at=d.get("started_at"),
        finished_at=d.get("finished_at"),
    )


# ──────────────────────── 异步触发 ────────────────────────


@router.post(
    "/evaluations",
    response_model=ResponseModel,
    status_code=202,
)
async def trigger_evaluate(
    body: EvaluateRequest,
    session: AsyncSession = Depends(get_db),
):
    """触发一次元数据评估（异步）。

    立即返 202 + {job_id, status: pending}；worker 后台调度实际评估。
    前端用 GET /evaluations/jobs/{job_id} 轮询状态。
    """
    # 先确认 dataset 存在（避免 enqueue 一个永远跑不出来的 job）
    from app.dao import dataset as dataset_dao

    ds_check = await dataset_dao.get_dataset(session=session, dataset_id=body.dataset_id)
    if not ds_check.get("ok"):
        return ResponseModel.fail(code=404, msg=ds_check.get("error", "dataset not found"))

    create_res = await job_dao.create_job(session=session, dataset_id=body.dataset_id)
    if not create_res.get("ok"):
        return ResponseModel.fail(
            code=500, msg=create_res.get("error", "create_job failed"),
        )

    job_id = create_res["job_id"]
    payload = _job_dict_to_response(
        {
            "id": job_id,
            "dataset_id": body.dataset_id,
            "status": "pending",
            "evaluation_id": None,
            "error": None,
            "elapsed_ms": None,
            "token_prompt": None,
            "token_completion": None,
            "token_total": None,
            "created_at": None,
            "started_at": None,
            "finished_at": None,
        }
    )
    return ResponseModel.success(
        payload.model_dump(),
        msg=f"评估任务已创建：job_id={job_id}",
    )


@router.get(
    "/evaluations/jobs/{job_id}",
    response_model=ResponseModel,
)
async def get_evaluate_job(
    job_id: int,
    session: AsyncSession = Depends(get_db),
):
    """查 job 状态。前端每 1.5s 轮询一次。"""
    res = await job_dao.get_job(session=session, job_id=job_id)
    if not res.get("ok"):
        return ResponseModel.fail(code=404, msg=res.get("error", "job not found"))

    payload = _job_dict_to_response(res["job"])
    return ResponseModel.success(payload.model_dump())


@router.delete(
    "/evaluations/jobs/{job_id}",
    response_model=ResponseModel,
)
async def cancel_evaluate_job(
    job_id: int,
    session: AsyncSession = Depends(get_db),
):
    """取消运行中的 job。

    - job 不存在 → 404
    - job 已完成 / 失败 → 409（不可取消）
    - worker 找不到该 running task（可能刚 claim 还没注册）→ 409
    - 取消信号已发 → 200
    """
    res = await job_dao.get_job(session=session, job_id=job_id)
    if not res.get("ok"):
        return ResponseModel.fail(code=404, msg=res.get("error", "job not found"))

    job = res["job"]
    if job["status"] not in ("pending", "running"):
        return ResponseModel.fail(
            code=409,
            msg=f"job is {job['status']}, cannot cancel",
        )

    cancelled = await worker.cancel_job(job_id)
    if not cancelled:
        return ResponseModel.fail(
            code=409,
            msg="job not currently running (worker has no active task for it)",
        )

    return ResponseModel.success({"job_id": job_id}, msg="取消信号已发送")


@router.get(
    "/evaluations/by-job/{job_id}",
    response_model=ResponseModel,
)
async def get_evaluation_by_job(
    job_id: int,
    session: AsyncSession = Depends(get_db),
):
    """job 完成后透传 evaluation 详情。

    job 不在 completed → 404
    evaluation 不存在 → 404
    """
    job_res = await job_dao.get_job(session=session, job_id=job_id)
    if not job_res.get("ok"):
        return ResponseModel.fail(code=404, msg=job_res.get("error", "job not found"))

    job = job_res["job"]
    evaluation_id = job.get("evaluation_id")
    if not evaluation_id or job.get("status") != "completed":
        return ResponseModel.fail(
            code=404,
            msg=f"job is {job['status']}, no evaluation available",
        )

    ev_res = await meta_eval_dao.get_evaluation(
        session=session, evaluation_id=evaluation_id,
    )
    if not ev_res.get("ok"):
        return ResponseModel.fail(code=404, msg=ev_res.get("error", "evaluation not found"))

    ev = ev_res["evaluation"]
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
    "/jobs",
    response_model=ResponseModel,
)
async def list_evaluate_jobs(
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
    """按 dataset_id 拉 jobs（按 created_at DESC）。"""
    res = await job_dao.list_jobs_by_dataset(
        session=session, dataset_id=dataset_id, page=page, size=size,
    )
    if not res.get("ok"):
        return ResponseModel.fail(code=500, msg=res.get("error", "list_jobs failed"))

    payload = JobListResponse(
        items=[
            JobListItem(
                job_id=it["id"],
                dataset_id=it["dataset_id"],
                status=it["status"],
                evaluation_id=it.get("evaluation_id"),
                error=it.get("error"),
                elapsed_ms=it.get("elapsed_ms"),
                token_total=it.get("token_total"),
                created_at=it.get("created_at"),
                started_at=it.get("started_at"),
                finished_at=it.get("finished_at"),
            )
            for it in res["items"]
        ],
        page=res["page"],
        size=res["size"],
        count=res["count"],
    )
    return ResponseModel.success(payload.model_dump())


# ──────────────────────── evaluation 详情（兼容） ────────────────────────


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
    """datasets 列表 + 每条 dataset 的最新 evaluation 摘要。"""
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