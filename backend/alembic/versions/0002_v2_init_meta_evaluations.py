"""0002 v2 init meta_evaluations

Revision ID: 0002_v2_init_meta_evaluations
Revises: 0001_v2_init_datasets
Create Date: 2026-06-28 18:30:00.000000

meta_evaluations 表（Phase 2）

字段：
- id               : BIGSERIAL PK
- dataset_id       : VARCHAR(64) — sha256(url) 64 位 hex（无 FK，应用层校验）
- score_total      : 0..405
- score_discover   : 0..100
- score_access     : 0..100
- score_interop    : 0..110
- score_reuse      : 0..75
- score_context    : 0..20
- grade            : Excellent / Good / Sufficient / Bad
- rule_scores      : JSONB（23 条 indicator 明细）
- llm_notes        : JSONB（soft_quality + improvement_suggestions）
- evaluation_content: TEXT（Markdown 报告）
- report_json      : JSONB（MetaEvaluateResult 原样存一份）
- created_at       : TIMESTAMPTZ

索引：
- idx_meta_eval_dataset : B-tree(dataset_id) — 按 dataset 过滤评估历史
- idx_meta_eval_grade   : B-tree(grade) — 按等级过滤
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0002_v2_init_meta_evaluations"
down_revision: Union[str, Sequence[str], None] = "0001_v2_init_datasets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "meta_evaluations",
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
            comment="sha256(url) 64 位 hex（应用层校验存在性，无 FK）",
        ),
        sa.Column("score_total", sa.Integer(), nullable=False),
        sa.Column("score_discover", sa.Integer(), nullable=False),
        sa.Column("score_access", sa.Integer(), nullable=False),
        sa.Column("score_interop", sa.Integer(), nullable=False),
        sa.Column("score_reuse", sa.Integer(), nullable=False),
        sa.Column("score_context", sa.Integer(), nullable=False),
        sa.Column(
            "grade",
            sa.String(length=16),
            nullable=False,
            comment="Excellent / Good / Sufficient / Bad",
        ),
        sa.Column(
            "rule_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="23 条 EU MQA indicator 明细",
        ),
        sa.Column(
            "llm_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="soft_quality_title/description + improvement_suggestions",
        ),
        sa.Column(
            "evaluation_content",
            sa.Text(),
            nullable=False,
            comment="Markdown 报告（service 层生成）",
        ),
        sa.Column(
            "report_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="MetaEvaluateResult 原样 JSON 备份",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_meta_eval_dataset",
        "meta_evaluations",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "idx_meta_eval_grade",
        "meta_evaluations",
        ["grade"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_meta_eval_grade", table_name="meta_evaluations")
    op.drop_index("idx_meta_eval_dataset", table_name="meta_evaluations")
    op.drop_table("meta_evaluations")