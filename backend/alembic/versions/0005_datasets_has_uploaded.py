"""0005 datasets has_uploaded

Revision ID: 0005_datasets_has_uploaded
Revises: 0004_meta_evaluation_uuid_id
Create Date: 2026-06-29 12:00:00.000000

datasets 表新增 has_uploaded 布尔位（Phase 3 数据采集标记）。
不沿用 status 枚举，避免与采集状态机耦合。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0005_datasets_has_uploaded"
down_revision: Union[str, Sequence[str], None] = "0004_meta_evaluation_uuid_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "datasets",
        sa.Column(
            "has_uploaded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否已上传过 data file（Phase 3 标记）",
        ),
    )


def downgrade() -> None:
    op.drop_column("datasets", "has_uploaded")