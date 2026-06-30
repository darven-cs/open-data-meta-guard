"""0008 add chat tables

Revision ID: 0008_add_chat_tables
Revises: 0007_dq_eval_init
Create Date: 2026-06-30 12:00:00.000000

conversations + chat_messages 表（Phase 6 数据故事 chatbot 对话持久化）。

conversations:
- id            UUID PK DEFAULT gen_random_uuid()
- title         VARCHAR(255) DEFAULT '新会话'
- created_at    TIMESTAMPTZ DEFAULT now()
- updated_at    TIMESTAMPTZ DEFAULT now()

chat_messages:
- id              UUID PK DEFAULT gen_random_uuid()
- conversation_id UUID FK → conversations.id ON DELETE CASCADE
- role            VARCHAR(16) NOT NULL  -- user / assistant
- content         TEXT DEFAULT ''
- chart_paths     JSONB DEFAULT '[]'
- kg_context      JSONB DEFAULT '{}'
- tool_steps      JSONB DEFAULT '[]'
- created_at      TIMESTAMPTZ DEFAULT now()

索引：
- idx_chat_messages_conversation : B-tree(conversation_id)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0008_add_chat_tables"
down_revision: Union[str, Sequence[str], None] = "0007_dq_eval_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="UUID PK",
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text("'新会话'"),
            comment="会话标题",
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

    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="UUID PK",
        ),
        sa.Column(
            "conversation_id",
            sa.dialects.postgresql.UUID(as_uuid=False),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK → conversations.id",
        ),
        sa.Column(
            "role",
            sa.String(length=16),
            nullable=False,
            comment="user / assistant",
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
            comment="Markdown 故事正文",
        ),
        sa.Column(
            "chart_paths",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment="[{chart_type, file_path, title}]",
        ),
        sa.Column(
            "kg_context",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
            comment="{entities, datasets} 溯源",
        ),
        sa.Column(
            "tool_steps",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'[]'::jsonb"),
            comment="[{tool, status}]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_chat_messages_conversation",
        "chat_messages",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_chat_messages_conversation", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_table("conversations")
