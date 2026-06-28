"""0001 v2 init datasets

Revision ID: 0001_v2_init_datasets
Revises:
Create Date: 2026-06-28 16:30:00.000000

v2.0 datasets 表（Phase 1）

字段：
- id           : sha256(url) 64 位 hex（主键，幂等去重）
- url          : 原始数据源 URL（UNIQUE）
- metadata     : JSONB（页面原始中文键字典，来自 ScrapResult.metadata）
- status       : pending / scraped / failed（采集状态机）
- created_at /
  updated_at   : 审计字段

索引：
- idx_datasets_metadata : GIN(metadata) — JSONB 字段内容检索
- idx_datasets_status   : B-tree(status) — 按状态过滤
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


revision: str = "0001_v2_init_datasets"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column(
            "id",
            sa.String(length=64),
            primary_key=True,
            comment="sha256(url) 64 位 hex，单射函数，幂等去重",
        ),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=text("'{}'::jsonb"),
            comment="页面原始中文键字典（来自 ScrapResult.metadata）",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=text("'pending'"),
            comment="pending / scraped / failed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_datasets_metadata",
        "datasets",
        ["metadata"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "idx_datasets_status",
        "datasets",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_datasets_status", table_name="datasets")
    op.drop_index("idx_datasets_metadata", table_name="datasets")
    op.drop_table("datasets")
