"""0006 data_downloads init

Revision ID: 0006_data_downloads_init
Revises: 0005_datasets_has_uploaded
Create Date: 2026-06-29 12:05:00.000000

data_downloads 表（Phase 3 数据采集人工上传登记）。

字段：
- id              : BIGSERIAL PK
- dataset_id      : VARCHAR(64) — sha256(url)，FK→datasets.id ON DELETE CASCADE
- file_name       : VARCHAR(255) — 用户原文件名
- file_path       : TEXT — 磁盘相对路径（settings.download_dir/uploads/{dataset_id}/{filename}）
- file_format     : VARCHAR(16) — csv / xlsx / json（小写）
- file_size       : BIGINT — 字节
- file_sha256     : VARCHAR(64) — sha256 hex
- source          : VARCHAR(16) — user_upload（保留 future source 字段）
- status          : VARCHAR(16) — uploaded（预留扩展）
- error_message   : TEXT — 失败原因
- created_at      : TIMESTAMPTZ

索引：
- idx_data_downloads_dataset : B-tree(dataset_id)
- idx_data_downloads_status  : B-tree(status)

注意：datasets.id ON DELETE CASCADE 仅清 DB 行，磁盘孤儿文件留待后续清理。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0006_data_downloads_init"
down_revision: Union[str, Sequence[str], None] = "0005_datasets_has_uploaded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "data_downloads",
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
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
            comment="sha256(url) 64 位 hex（FK→datasets.id）",
        ),
        sa.Column(
            "file_name",
            sa.String(length=255),
            nullable=False,
            comment="用户原文件名",
        ),
        sa.Column(
            "file_path",
            sa.Text(),
            nullable=False,
            comment="磁盘相对路径",
        ),
        sa.Column(
            "file_format",
            sa.String(length=16),
            nullable=False,
            comment="csv / xlsx / json（小写）",
        ),
        sa.Column(
            "file_size",
            sa.BigInteger(),
            nullable=False,
            comment="字节",
        ),
        sa.Column(
            "file_sha256",
            sa.String(length=64),
            nullable=False,
            comment="sha256 hex",
        ),
        sa.Column(
            "source",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'user_upload'"),
            comment="user_upload（预留扩展）",
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'uploaded'"),
            comment="uploaded（预留扩展）",
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="失败原因",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_data_downloads_dataset",
        "data_downloads",
        ["dataset_id"],
        unique=False,
    )
    op.create_index(
        "idx_data_downloads_status",
        "data_downloads",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_data_downloads_status", table_name="data_downloads")
    op.drop_index("idx_data_downloads_dataset", table_name="data_downloads")
    op.drop_table("data_downloads")