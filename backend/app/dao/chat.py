"""conversations + chat_messages 表 DAO。

设计要点：
- 函数签名接 Python 类型（str / dict），不接 ORM 对象
- 错误统一返回 `{"ok": False, "error": "..."}`；不抛业务异常
- session.commit() 在 DAO 内显式调用
- 删 conversation 级联删所有消息（DB 级 ON DELETE CASCADE）
"""
from typing import Any

from sqlalchemy import delete as sa_delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log import logger
from app.model.chat import ChatMessage, Conversation


# ──────────────────────── helpers ────────────────────────


def _conv_to_dict(c: Conversation) -> dict[str, Any]:
    return {
        "id": c.id,
        "title": c.title,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _msg_to_dict(m: ChatMessage) -> dict[str, Any]:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "chart_paths": m.chart_paths or [],
        "kg_context": m.kg_context or {},
        "tool_steps": m.tool_steps or [],
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# ──────────────────────── Conversations CRUD ────────────────────────


async def create_conversation(session: AsyncSession, title: str = "新会话") -> dict:
    """新建会话。

    Returns:
        {"ok": True, "conversation": {...}}
    """
    conv = Conversation(title=title)
    session.add(conv)
    try:
        await session.commit()
        await session.refresh(conv)
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"create_conversation integrity error: {e}"}
    return {"ok": True, "conversation": _conv_to_dict(conv)}


async def list_conversations(session: AsyncSession) -> dict:
    """列出所有会话（按 updated_at DESC）。

    Returns:
        {"ok": True, "conversations": [...]}
    """
    stmt = select(Conversation).order_by(Conversation.updated_at.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {"ok": True, "conversations": [_conv_to_dict(r) for r in rows]}


async def get_conversation(session: AsyncSession, conv_id: str) -> dict:
    """按 id 查会话。

    Returns:
        {"ok": True, "conversation": {...}} / {"ok": False, "error": "..."}
    """
    if not conv_id:
        return {"ok": False, "error": "conv_id is required"}
    row = await session.get(Conversation, conv_id)
    if row is None:
        return {"ok": False, "error": f"conversation not found: {conv_id}"}
    return {"ok": True, "conversation": _conv_to_dict(row)}


async def delete_conversation(session: AsyncSession, conv_id: str) -> dict:
    """删除会话（级联删所有消息）。

    Returns:
        {"ok": True, "deleted": True} / {"ok": False, "error": "..."}
    """
    if not conv_id:
        return {"ok": False, "error": "conv_id is required"}
    row = await session.get(Conversation, conv_id)
    if row is None:
        return {"ok": False, "error": f"conversation not found: {conv_id}"}
    await session.execute(
        sa_delete(Conversation).where(Conversation.id == conv_id)
    )
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"delete_conversation integrity error: {e}"}
    return {"ok": True, "deleted": True}


# ──────────────────────── Messages CRUD ────────────────────────


async def add_message(
    session: AsyncSession,
    conv_id: str,
    role: str,
    content: str = "",
    chart_paths: list | None = None,
    kg_context: dict | None = None,
    tool_steps: list | None = None,
) -> dict:
    """插入一条聊天消息。

    Returns:
        {"ok": True, "message": {...}} / {"ok": False, "error": "..."}
    """
    if not conv_id:
        return {"ok": False, "error": "conv_id is required"}
    if role not in ("user", "assistant"):
        return {"ok": False, "error": f"invalid role: {role}"}

    msg = ChatMessage(
        conversation_id=conv_id,
        role=role,
        content=content,
        chart_paths=chart_paths or [],
        kg_context=kg_context or {},
        tool_steps=tool_steps or [],
    )
    session.add(msg)
    try:
        await session.commit()
        await session.refresh(msg)
    except IntegrityError as e:
        await session.rollback()
        return {"ok": False, "error": f"add_message integrity error: {e}"}

    # 更新会话 updated_at
    conv = await session.get(Conversation, conv_id)
    if conv:
        conv.updated_at = msg.created_at
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()

    return {"ok": True, "message": _msg_to_dict(msg)}


async def get_messages(session: AsyncSession, conv_id: str) -> dict:
    """按会话 id 获取所有消息（按 created_at ASC）。

    Returns:
        {"ok": True, "messages": [...]} / {"ok": False, "error": "..."}
    """
    if not conv_id:
        return {"ok": False, "error": "conv_id is required"}

    stmt = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conv_id)
        .order_by(ChatMessage.created_at.asc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return {"ok": True, "messages": [_msg_to_dict(r) for r in rows]}


__all__ = [
    "create_conversation",
    "list_conversations",
    "get_conversation",
    "delete_conversation",
    "add_message",
    "get_messages",
]
