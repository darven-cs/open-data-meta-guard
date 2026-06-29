"""0007 dq_eval init

Revision ID: 0007_dq_eval_init
Revises: 0006_data_downloads_init
Create Date: 2026-06-29 18:00:00.000000

data_quality_evaluations 表（Phase 4 数据质量评估结果）。

字段：
- id                  : BIGSERIAL PK
- dataset_id          : VARCHAR(64) — sha256(url) 64 位 hex
- data_download_id    : BIGINT — FK→data_downloads.id ON DELETE CASCADE
- evaluation_content  : TEXT — Markdown 报告
- summary             : JSONB — 行数/列数/缺失率/重复率等
- issues              : JSONB — pandera schema 校验问题列表
- created_at          : TIMESTAMPTZ

索引：
- idx_dq_eval_dataset  : B-tree(dataset_id)
- idx_dq_eval_download : B-tree(data_download_id)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0007_dq_eval_init"
down_revision: Union[str, Sequence[str], None] = "0006_data_downloads_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_quality_evaluations",
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            comment="BIGSERIAL PK",
        ),
        sa.Column(
            "dataset_id",
            sa.String(length=64),
            nullable=False,
            comment="sha256(url) 64 位 hex",
        ),
        sa.Column(
            "data_download_id",
            sa.BigInteger(),
            sa.ForeignKey("data_downloads.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK→data_downloads.id",
        ),
        sa.Column(
            "evaluation_content",
            sa.Text(),
            nullable=False,
            comment="Markdown 报告",
        ),
        sa.Column(
            "summary",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="行数/列数/缺失率/重复率等统计摘要",
        ),
        sa.Column(
            "issues",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="pandera schema 校验问题列表",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_dq_eval_dataset",
        "data_quality_evaluations",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "idx_dq_eval_download",
        "data_quality_evaluations",
        ["data_download_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_dq_eval_download", table_name="data_quality_evaluations")
    op.drop_index("idx_dq_eval_dataset", table_name="data_quality_evaluations")
    op.drop_table("data_quality_evaluations")
