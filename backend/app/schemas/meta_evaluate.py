"""元数据评估 API schema — `/meta-evaluate/evaluations/*` 路由请求/响应模型。

请求：EvaluateRequest（dataset_id 必填，64 位 hex）
响应：EvaluateResponse / EvaluationDetail / EvaluationListItem / EvaluationListResponse
"""
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────── 请求体 ────────────────────────


class EvaluateRequest(BaseModel):
    """POST /meta-evaluate/evaluations 请求体。"""

    dataset_id: str = Field(
        min_length=64,
        max_length=64,
        description="sha256(url) 64 位 hex（指向已采集的 dataset）",
    )


# ──────────────────────── 响应项 ────────────────────────


class EvaluateResponse(BaseModel):
    """POST /evaluations 响应体（触发评估后返回新生成的 evaluation_id）。"""

    ok: bool = Field(description="整体成功标记")
    evaluation_id: int = Field(description="新写入的 evaluation id")
    dataset_id: str = Field(description="被评估的 dataset id")
    score_total: int = Field(description="总分（0-405）")
    grade: str = Field(description="Excellent / Good / Sufficient / Bad")
    created_at: str = Field(description="评估时间 ISO 8601")


class EvaluationListItem(BaseModel):
    """GET /evaluations 列表单条。"""

    id: int
    dataset_id: str
    score_total: int
    grade: str
    created_at: Optional[str] = None


class EvaluationListResponse(BaseModel):
    """GET /evaluations 列表响应。"""

    items: list[EvaluationListItem]
    page: int
    size: int
    count: int


class EvaluationDetail(BaseModel):
    """GET /evaluations/{evaluation_id} 详情响应。"""

    id: int
    dataset_id: str
    score_total: int
    score_discover: int
    score_access: int
    score_interop: int
    score_reuse: int
    score_context: int
    grade: str
    rule_scores: dict = Field(default_factory=dict)
    llm_notes: dict = Field(default_factory=dict)
    evaluation_content: str
    report_json: Optional[dict] = None
    created_at: Optional[str] = None


# ──────────────────────── datasets + latest eval ────────────────────────


class LatestEvaluation(BaseModel):
    """dataset 的最新一次 evaluation 摘要（用于评估页行内展示）。"""

    id: int
    score_total: int
    grade: str
    created_at: Optional[str] = None


class DatasetEvalItem(BaseModel):
    """GET /meta-evaluate/datasets 列表单条（含最新 evaluation 摘要）。"""

    id: str = Field(description="sha256(url) 64 位 hex")
    url: str
    status: str = Field(description="pending / scraped / failed")
    metadata: dict = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    latest_evaluation: Optional[LatestEvaluation] = Field(
        default=None,
        description="最新一次 evaluation 摘要；None 表示尚未评估",
    )


class DatasetEvalListResponse(BaseModel):
    """GET /meta-evaluate/datasets 列表响应。"""

    items: list[DatasetEvalItem]
    page: int
    size: int
    count: int