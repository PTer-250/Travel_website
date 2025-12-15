"""Schemas for agent chat and conversation APIs."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationSummary(BaseModel):
    """Lightweight conversation info for lists."""

    id: int
    title: str
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_message_preview: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    items: List[ConversationSummary]


class ChatMessageRequest(BaseModel):
    """Incoming chat message payload."""

    content: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[int] = None


class ChatMessage(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_args: Optional[dict] = None
    tool_output: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    conversation_id: int
    messages: List[ChatMessage]


class MessageListResponse(BaseModel):
    items: List[ChatMessage]
