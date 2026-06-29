"""0004 meta_evaluation_uuid_id

Revision ID: 0004_meta_evaluation_uuid_id
Revises: 0003_meta_eval_jobs
Create Date: 2026-06-28 21:00:00.000000

把 meta_evaluations.id 和 meta_evaluation_jobs.evaluation_id 从 BigSerial/BigInt
改成 VARCHAR(36)，由 app 层用 uuid.uuid4() 预分配，实现"触发瞬间即返 evaluation_id"。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0004_meta_evaluation_uuid_id"
down_revision: Union[str, Sequence[str], None] = "0003_meta_eval_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) meta_evaluations.id: 去掉 BIGSERIAL 默认值（依赖序列），再改类型
    op.execute("ALTER TABLE meta_evaluations ALTER COLUMN id DROP DEFAULT")
    op.alter_column(
        "meta_evaluations",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.String(length=36),
        postgresql_using="id::varchar(36)",
        existing_nullable=False,
        autoincrement=False,
        existing_comment="BIGSERIAL PK",
    )

    # 2) meta_evaluation_jobs.evaluation_id: bigint → varchar(36)
    op.alter_column(
        "meta_evaluation_jobs",
        "evaluation_id",
        existing_type=sa.BigInteger(),
        type_=sa.String(length=36),
        postgresql_using="evaluation_id::varchar(36)",
        existing_nullable=True,
        existing_comment="成功后写入的 meta_evaluations.id",
    )

    # 3) PK 不再依赖序列，清理兜底
    op.execute("DROP SEQUENCE IF EXISTS meta_evaluations_id_seq")


def downgrade() -> None:
    op.alter_column(
        "meta_evaluations",
        "id",
        existing_type=sa.String(length=36),
        type_=sa.BigInteger(),
        postgresql_using="id::bigint",
        existing_nullable=False,
        autoincrement=True,
        existing_comment="UUID4 字符串，由 app 层在触发时生成",
    )
    op.alter_column(
        "meta_evaluation_jobs",
        "evaluation_id",
        existing_type=sa.String(length=36),
        type_=sa.BigInteger(),
        postgresql_using="evaluation_id::bigint",
        existing_nullable=True,
        existing_comment="UUID4 字符串，触发时预分配（无 FK）",
    )