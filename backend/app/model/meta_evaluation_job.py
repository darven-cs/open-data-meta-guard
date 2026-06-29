"""meta_evaluation_jobs 表 — 异步评估作业。

字段：
- id              : BIGSERIAL PK (job_id)
- dataset_id      : sha256(url) 64 位 hex
- status          : pending / running / completed / failed / cancelled
- evaluation_id   : UUID4 字符串，触发时预分配（无 FK）
- error           : 失败/取消原因
- elapsed_ms      : 总耗时
- token_prompt    : LLM prompt tokens
- token_completion: LLM completion tokens
- token_total     : 合计
- tool_calls_json : agent 调用工具记录（JSONB）
- reasoning_log   : reasoning_content 拼接（TEXT，截断 16KB）
- started_at      : claim 时
- finished_at     : 终态时
- created_at      : 入库时

索引：
- idx_meta_eval_job_dataset : B-tree(dataset_id)
- idx_meta_eval_job_status  : B-tree(status) — worker 高频按 status 扫
"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MetaEvaluationJob(Base):
    """异步评估作业表（v2 worker 调度用）。"""

    __tablename__ = "meta_evaluation_jobs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    dataset_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="sha256(url) 64 位 hex（应用层校验存在性）",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'pending'"),
        comment="pending / running / completed / failed / cancelled",
    )
    evaluation_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        comment="UUID4 字符串，触发时预分配（无 FK）",
    )
    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="失败/取消原因",
    )
    elapsed_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="总耗时（ms）",
    )
    token_prompt: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="LLM prompt tokens",
    )
    token_completion: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="LLM completion tokens",
    )
    token_total: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="prompt + completion",
    )
    tool_calls_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="agent tool_calls 记录",
    )
    reasoning_log: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="reasoning_content 拼接（截断到 16KB）",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="worker claim 时",
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="终态时",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_meta_eval_job_dataset", "dataset_id"),
        Index("idx_meta_eval_job_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<MetaEvaluationJob id={self.id} dataset_id={self.dataset_id!r} "
            f"status={self.status!r}>"
        )