"""data_downloads 表 — 数据采集（人工上传）登记。

字段：
- id              : BIGSERIAL PK
- dataset_id      : VARCHAR(64) — sha256(url)，FK→datasets.id ON DELETE CASCADE
- file_name       : VARCHAR(255) — 用户原文件名
- file_path       : TEXT — 磁盘路径（settings.download_dir/uploads/{dataset_id}/{filename}）
- file_format     : VARCHAR(16) — csv / xlsx / json（小写）
- file_size       : BIGINT — 字节
- file_sha256     : VARCHAR(64) — sha256 hex
- source          : VARCHAR(16) — user_upload（预留扩展）
- status          : VARCHAR(16) — uploaded（预留扩展）
- error_message   : TEXT — 失败原因
- created_at      : TIMESTAMPTZ

索引：
- idx_data_downloads_dataset : B-tree(dataset_id)
- idx_data_downloads_status  : B-tree(status)

注意：
- datasets.id ON DELETE CASCADE 仅清 DB 行；磁盘孤儿文件留待后续清理。
- file_path 是绝对路径字符串，service 层在写入前用 safe_path 防御路径穿越。
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class DataDownload(Base):
    """数据采集（人工上传）登记表。"""

    __tablename__ = "data_downloads"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="BIGSERIAL PK",
    )
    dataset_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        comment="sha256(url) 64 位 hex（FK→datasets.id）",
    )
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="用户原文件名",
    )
    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="磁盘绝对路径",
    )
    file_format: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="csv / xlsx / json（小写）",
    )
    file_size: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        comment="字节",
    )
    file_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="sha256 hex",
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'user_upload'"),
        comment="user_upload（预留扩展）",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'uploaded'"),
        comment="uploaded（预留扩展）",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="失败原因",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_data_downloads_dataset", "dataset_id"),
        Index("idx_data_downloads_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<DataDownload id={self.id} dataset_id={self.dataset_id!r} "
            f"format={self.file_format!r} size={self.file_size}>"
        )