"""数据故事 chatbot API Schema。"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建会话请求。"""
    title: str = Field(default="新会话", description="会话标题")


class ConversationResponse(BaseModel):
    """会话响应。"""
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ConversationList(BaseModel):
    """会话列表响应。"""
    conversations: list[ConversationResponse]


class MessageCreate(BaseModel):
    """创建消息请求。"""
    conversation_id: str = Field(description="会话 ID")
    role: str = Field(description="user / assistant")
    content: str = Field(default="", description="Markdown 故事正文")
    chart_paths: list[dict] = Field(default_factory=list)
    kg_context: dict = Field(default_factory=dict)
    tool_steps: list[dict] = Field(default_factory=list)


class MessageResponse(BaseModel):
    """消息响应。"""
    id: str
    conversation_id: str
    role: str
    content: str
    chart_paths: list = Field(default_factory=list)
    kg_context: dict = Field(default_factory=dict)
    tool_steps: list = Field(default_factory=list)
    created_at: Optional[str] = None


class MessageList(BaseModel):
    """消息列表响应。"""
    messages: list[MessageResponse]


class ChatStreamRequest(BaseModel):
    """SSE 流式请求体。"""
    message: str = Field(description="用户消息文本")
    conversation_id: Optional[str] = Field(default=None, description="可选会话 ID")
