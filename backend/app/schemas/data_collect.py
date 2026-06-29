"""数据采集（人工上传）schema — `/data-collect/*` 路由请求/响应模型。

响应：UploadResponse / DownloadListItem / DownloadListResponse / DownloadDetailResponse
辅助：DatasetSelectItem / DatasetSelectListResponse（上拉源）
"""
from typing import Optional

from pydantic import BaseModel, Field


# ──────────────────────── 上传响应 ────────────────────────


class UploadResponse(BaseModel):
    """POST /data-collect/upload 响应体（落盘 + 落库后回写）。"""

    download_id: int = Field(description="新写入的 data_downloads.id")
    dataset_id: str = Field(description="关联的 dataset id")
    file_name: str
    file_format: str = Field(description="csv / xlsx / json")
    file_size: int = Field(description="字节")
    file_sha256: str = Field(description="sha256 hex")
    created_at: Optional[str] = None


# ──────────────────────── 列表 / 详情 ────────────────────────


class DownloadListItem(BaseModel):
    """GET /data-collect 列表单条。"""

    id: int
    dataset_id: str
    file_name: str
    file_format: str
    file_size: int
    file_sha256: str
    source: str
    status: str
    created_at: Optional[str] = None


class DownloadListResponse(BaseModel):
    """GET /data-collect 列表响应。"""

    items: list[DownloadListItem]
    page: int
    size: int
    count: int


class DownloadDetailResponse(BaseModel):
    """GET /data-collect/{id} 详情响应。"""

    id: int
    dataset_id: str
    file_name: str
    file_path: str
    file_format: str
    file_size: int
    file_sha256: str
    source: str
    status: str
    error_message: Optional[str] = None
    created_at: Optional[str] = None


# ──────────────────────── 上拉源 ────────────────────────


class DatasetSelectItem(BaseModel):
    """GET /data-collect/datasets 列表单条（按 dataset 维度）。"""

    id: str
    url: str
    has_uploaded: bool
    status: str = Field(description="pending / scraped / failed")
    created_at: Optional[str] = None


class DatasetSelectListResponse(BaseModel):
    """GET /data-collect/datasets 列表响应（分页）。"""

    items: list[DatasetSelectItem]
    page: int
    size: int
    count: int