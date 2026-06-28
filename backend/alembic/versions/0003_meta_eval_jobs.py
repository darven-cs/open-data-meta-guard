"""0003 v2 init meta_evaluation_jobs

Revision ID: 0003_meta_eval_jobs
Revises: 0002_v2_init_meta_evaluations
Create Date: 2026-06-28 20:00:00.000000

meta_evaluation_jobs 表（异步评估作业表，v2.0 Phase 3）

字段：
- id              : BIGSERIAL PK
- dataset_id      : VARCHAR(64)
- status          : pending / running / completed / failed / cancelled
- evaluation_id   : BIGINT NULL（成功后指向 meta_evaluations.id）
- error           : TEXT NULL（失败/取消原因）
- elapsed_ms      : INT NULL（总耗时）
- token_prompt    : INT NULL
- token_completion: INT NULL
- token_total     : INT NULL
- tool_calls_json : JSONB NULL
- reasoning_log   : TEXT NULL
- started_at      : TIMESTAMPTZ NULL
- finished_at     : TIMESTAMPTZ NULL
- created_at      : TIMESTAMPTZ NOT NULL DEFAULT now()

索引：
- idx_meta_eval_job_dataset : B-tree(dataset_id)
- idx_meta_eval_job_status  : B-tree(status) — worker 高频按 status 扫
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0003_meta_eval_jobs"
down_revision: Union[str, Sequence[str], None] = "0002_v2_init_meta_evaluations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meta_evaluation_jobs",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "dataset_id",
            sa.String(length=64),
            nullable=False,
            comment="sha256(url) 64 位 hex",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="pending / running / completed / failed / cancelled",
        ),
        sa.Column(
            "evaluation_id",
            sa.BigInteger(),
            nullable=True,
            comment="成功后写入的 meta_evaluations.id",
        ),
        sa.Column(
            "error",
            sa.Text(),
            nullable=True,
            comment="失败/取消原因",
        ),
        sa.Column(
            "elapsed_ms",
            sa.Integer(),
            nullable=True,
            comment="总耗时（ms）",
        ),
        sa.Column(
            "token_prompt",
            sa.Integer(),
            nullable=True,
            comment="LLM prompt tokens",
        ),
        sa.Column(
            "token_completion",
            sa.Integer(),
            nullable=True,
            comment="LLM completion tokens",
        ),
        sa.Column(
            "token_total",
            sa.Integer(),
            nullable=True,
            comment="prompt + completion",
        ),
        sa.Column(
            "tool_calls_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="agent tool_calls 记录",
        ),
        sa.Column(
            "reasoning_log",
            sa.Text(),
            nullable=True,
            comment="reasoning_content 拼接（截断到 16KB）",
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="worker claim 时",
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="终态时",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_meta_eval_job_dataset",
        "meta_evaluation_jobs",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "idx_meta_eval_job_status",
        "meta_evaluation_jobs",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_meta_eval_job_status", table_name="meta_evaluation_jobs")
    op.drop_index("idx_meta_eval_job_dataset", table_name="meta_evaluation_jobs")
    op.drop_table("meta_evaluation_jobs")