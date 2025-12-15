"""Agent conversation and message models."""

from typing import List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship

from .base import BaseModel, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from .users import User


class Conversation(TimestampMixin, BaseModel, table=True):
    """A chat session between a user and the AI agent."""

    __tablename__ = "agent_conversations"

    title: str = Field(max_length=200, index=True)
    summary: Optional[str] = Field(default=None, max_length=500)
    user_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)

    messages: List["Message"] = Relationship(
        back_populates="conversation",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Message(TimestampMixin, BaseModel, table=True):
    """A single message in a conversation."""

    __tablename__ = "agent_messages"

    conversation_id: int = Field(foreign_key="agent_conversations.id", index=True)
    role: str = Field(max_length=32, index=True)
    content: str = Field(default="")
    tool_name: Optional[str] = Field(default=None, index=True)
    tool_call_id: Optional[str] = Field(default=None, index=True, max_length=128)
    tool_args: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    tool_output: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))

    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
