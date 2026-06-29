"""数据质量评估 API schema — `/data-quality/*` 请求/响应模型。

请求：QualityRequest（data_download_id 必填）
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


# ──────────────────────── 请求体 ────────────────────────


class QualityRequest(BaseModel):
    """POST /data-quality 请求体。"""

    data_download_id: int = Field(
        description="data_downloads.id（指向已上传的数据文件）",
    )


# ──────────────────────── 响应项 ────────────────────────


class QualityResponse(BaseModel):
    """POST /data-quality 响应体。"""

    ok: bool
    evaluation_id: int
    data_download_id: int
    created_at: str = Field(description="ISO 8601")


class QualityListItem(BaseModel):
    """GET /data-quality 列表单条。"""

    id: int
    dataset_id: str
    data_download_id: int
    file_name: Optional[str] = None
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class QualityListResponse(BaseModel):
    """GET /data-quality 列表响应。"""

    items: list[QualityListItem]
    page: int
    size: int
    count: int


class QualityDetail(BaseModel):
    """GET /data-quality/{id} 详情响应。"""

    id: int
    dataset_id: str
    data_download_id: int
    evaluation_content: str
    summary: dict[str, Any] = Field(default_factory=dict)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    created_at: Optional[str] = None


# ──────────────────────── downloads + latest eval ────────────────────────


class LatestQualitySummary(BaseModel):
    """data_download 的最新一次 quality eval 摘要。"""

    id: int
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class DownloadWithQualityItem(BaseModel):
    """GET /data-quality/downloads 列表单条。"""

    id: int = Field(description="data_download id")
    dataset_id: str
    file_name: str
    file_format: str
    file_size: int
    file_sha256: str
    source: str
    status: str
    created_at: Optional[str] = None
    latest_evaluation: Optional[LatestQualitySummary] = None


class DownloadWithQualityListResponse(BaseModel):
    """GET /data-quality/downloads 列表响应。"""

    items: list[DownloadWithQualityItem]
    page: int
    size: int
    count: int
