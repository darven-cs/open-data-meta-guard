"""
元数据采集 schema — `/meta-collect/datasets/*` 路由请求/响应模型。

设计要点：
- 请求模型：IngestRequest / UpdateRequest（绑 FastAPI body）
- 响应模型：IngestItem / IngestResponse / DatasetListResponse / DatasetDetailResponse
- metadata 字段为 dict（页面原始中文键字典），与 datasets.metadata JSONB 对应
- status 三态：pending / scraped / failed
"""
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────── 请求体 ────────────────────────


class IngestRequest(BaseModel):
    """POST /meta-collect/datasets/ingest 请求体。

    v2.0 同步实现：urls 同步遍历逐个抓取（不走后台）。
    """

    urls: list[str] = Field(
        min_length=1,
        max_length=50,
        description="1..50 个数据源 URL（http/https，去重后逐个抓取）",
    )


class UpdateRequest(BaseModel):
    """PUT /meta-collect/datasets/{dataset_id} 请求体。

    语义：整块覆盖 metadata；status 业务上由后端管控，不开放给前端修改。
    """

    metadata: dict = Field(
        ...,
        description="新的 metadata JSON 对象（整块覆盖 datasets.metadata）",
    )


# ──────────────────────── 响应项 ────────────────────────


class IngestItem(BaseModel):
    """POST /datasets/ingest 单条结果。"""

    url: str = Field(description="原始 URL")
    dataset_id: str = Field(description="sha256(url) 64 位 hex")
    status: str = Field(description="scraped / failed")
    error_message: Optional[str] = Field(
        default=None,
        description="失败原因（status='failed' 时填）",
    )


class IngestResponse(BaseModel):
    """POST /datasets/ingest 响应体。"""

    ok: bool = Field(description="整体成功标记")
    items: list[IngestItem] = Field(description="逐 URL 抓取结果")
    success_count: int = Field(description="成功的 URL 数（status='scraped'）")
    failed_count: int = Field(description="失败的 URL 数（status='failed'）")


class DatasetListItem(BaseModel):
    """GET /datasets 列表单条。"""

    id: str
    url: str
    metadata: dict = Field(default_factory=dict)
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class DatasetListResponse(BaseModel):
    """GET /datasets 列表响应。"""

    items: list[DatasetListItem]
    page: int
    size: int
    count: int


class DatasetDetailResponse(BaseModel):
    """GET /datasets/{dataset_id} 详情响应。"""

    id: str
    url: str
    metadata: dict = Field(default_factory=dict)
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
