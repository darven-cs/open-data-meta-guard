"""conversations + chat_messages 表 — 数据故事 chatbot 对话持久化。

字段：
- conversations: id (UUID PK), title, created_at, updated_at
- chat_messages: id (UUID PK), conversation_id (FK), role, content (Markdown),
  chart_paths (JSONB), kg_context (JSONB), tool_steps (JSONB), created_at

关系：
- conversations.id ON DELETE CASCADE → chat_messages.conversation_id
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Conversation(Base):
    """聊天会话表。"""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="UUID PK",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=func.text("'新会话'"),
        comment="会话标题",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id!r} title={self.title!r}>"


class ChatMessage(Base):
    """聊天消息表。"""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        comment="UUID PK",
    )
    conversation_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK → conversations.id",
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="user / assistant",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=func.text("''"),
        comment="Markdown 故事正文",
    )
    chart_paths: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=func.text("'[]'::jsonb"),
        comment="[{chart_type, file_path, title}]",
    )
    kg_context: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=func.text("'{}'::jsonb"),
        comment="{entities, datasets} 溯源",
    )
    tool_steps: Mapped[list | None] = mapped_column(
        JSONB,
        nullable=True,
        server_default=func.text("'[]'::jsonb"),
        comment="[{tool, status}]",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("idx_chat_messages_conversation", "conversation_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ChatMessage id={self.id!r} conversation_id={self.conversation_id!r} "
            f"role={self.role!r}>"
        )
