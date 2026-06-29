"""
datasets 表 — 抓取的原始元数据（根表）。

字段：
- id           : sha256(url) 64 位 hex（主键，单射函数，幂等去重）
- url          : 原始数据源 URL（UNIQUE）
- metadata     : JSONB（ScrapResult.metadata 整个对象，页面原始中文键字典）
- status       : pending / scraped / failed（采集状态机）
- created_at /
  updated_at   : 审计字段

无 FK 约定：
- 其他 Phase 子表（meta_evaluations 等）的 dataset_id 字段不是 FK，
  应用层通过 safe_write_dataset_id() 守。

设计选择：
- Python 属性叫 `metadata_`（避开 Declarative API 的 `metadata` 保留名），
  列名是 `metadata`；DAO 层用 `ds.metadata_ = ...` 写入。
- API 层对外暴露 `metadata`（不带下划线），由 DAO 的 _to_dict 负责映射。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Dataset(Base):
    """抓取的原始元数据（根表）。"""

    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        comment="sha256(url) 64 位 hex，单射函数，幂等去重",
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    # Python 属性叫 metadata_；列名 metadata（避免 Declarative API 保留字冲突）
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="页面原始中文键字典（来自 ScrapResult.metadata）",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'pending'"),
        comment="pending / scraped / failed",
    )
    has_uploaded: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        comment="是否已上传过 data file（Phase 3 标记）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("idx_datasets_metadata", "metadata", postgresql_using="gin"),
        Index("idx_datasets_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id!r} status={self.status!r}>"
