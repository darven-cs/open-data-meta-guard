"""data_quality_evaluations 表。

字段：
- id                  : BIGSERIAL PK
- dataset_id          : sha256(url) 64 位 hex
- data_download_id    : FK→data_downloads.id ON DELETE CASCADE
- evaluation_content  : TEXT（Markdown 报告）
- summary             : JSONB（行数/列数/缺失率/重复率等）
- issues              : JSONB（pandera schema 校验问题列表）
- created_at          : TIMESTAMPTZ
"""
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DataQualityEvaluation(Base):
    """数据质量评估结果。"""

    __tablename__ = "data_quality_evaluations"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    dataset_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="sha256(url) 64 位 hex",
    )
    data_download_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("data_downloads.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK→data_downloads.id",
    )
    evaluation_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Markdown 报告",
    )
    summary: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="行数/列数/缺失率/重复率等统计摘要",
    )
    issues: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
        comment="pandera schema 校验问题列表",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_dq_eval_dataset", "dataset_id"),
        Index("idx_dq_eval_download", "data_download_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<DataQualityEvaluation id={self.id} "
            f"dataset_id={self.dataset_id!r} "
            f"data_download_id={self.data_download_id}>"
        )
