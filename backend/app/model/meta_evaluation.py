"""meta_evaluations 表 — EU MQA 405 分制评估结果。

字段：
- id                : BIGSERIAL PK
- dataset_id        : sha256(url) 64 位 hex（无 FK）
- score_total       : 0..405
- score_discover    : 0..100  Findability
- score_access      : 0..100  Accessibility
- score_interop     : 0..110  Interoperability
- score_reuse       : 0..75   Reusability
- score_context     : 0..20   Contextuality
- grade             : Excellent / Good / Sufficient / Bad
- rule_scores       : JSONB（23 条 indicator 明细）
- llm_notes         : JSONB（soft_quality + improvement_suggestions）
- evaluation_content: TEXT（Markdown 报告）
- report_json       : JSONB（MetaEvaluateResult 原样）
- created_at        : TIMESTAMPTZ

无 FK：
- dataset_id 应用层校验存在性（service 层调 dataset_dao.get_dataset）。
"""
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MetaEvaluation(Base):
    """EU MQA 405 分制评估结果。"""

    __tablename__ = "meta_evaluations"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    dataset_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="sha256(url) 64 位 hex（应用层校验存在性，无 FK）",
    )
    score_total: Mapped[int] = mapped_column(Integer, nullable=False)
    score_discover: Mapped[int] = mapped_column(Integer, nullable=False)
    score_access: Mapped[int] = mapped_column(Integer, nullable=False)
    score_interop: Mapped[int] = mapped_column(Integer, nullable=False)
    score_reuse: Mapped[int] = mapped_column(Integer, nullable=False)
    score_context: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="Excellent / Good / Sufficient / Bad",
    )
    rule_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="23 条 EU MQA indicator 明细",
    )
    llm_notes: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="soft_quality_title/description + improvement_suggestions",
    )
    evaluation_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Markdown 报告（service 层生成）",
    )
    report_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="MetaEvaluateResult 原样 JSON 备份",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_meta_eval_dataset", "dataset_id"),
        Index("idx_meta_eval_grade", "grade"),
    )

    def __repr__(self) -> str:
        return (
            f"<MetaEvaluation id={self.id} dataset_id={self.dataset_id!r} "
            f"score_total={self.score_total} grade={self.grade!r}>"
        )