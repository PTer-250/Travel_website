"""Data access for agent conversations and messages."""

from __future__ import annotations

from datetime import datetime, UTC
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.agent import Conversation, Message


class AgentRepository:
    """CRUD operations for conversations and messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_conversation(self, *, title: str, user_id: Optional[UUID]) -> Conversation:
        conversation = Conversation(title=title, user_id=user_id)
        self.session.add(conversation)
        await self.session.commit()
        await self.session.refresh(conversation)
        return conversation

    async def get_conversation(self, conversation_id: int, *, user_id: Optional[UUID]) -> Optional[Conversation]:
        query = select(Conversation).where(Conversation.id == conversation_id)
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list_conversations(self, *, user_id: Optional[UUID], limit: int = 20) -> List[Conversation]:
        query = select(Conversation).order_by(desc(Conversation.updated_at)).limit(limit)
        if user_id:
            query = query.where(Conversation.user_id == user_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def add_message(
        self,
        *,
        conversation_id: int,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        tool_args: Optional[dict] = None,
        tool_output: Optional[dict] = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_args=tool_args,
            tool_output=tool_output,
        )
        self.session.add(message)

        await self.session.execute(
            select(Conversation).where(Conversation.id == conversation_id).with_for_update()
        )
        conversation = await self.get_conversation(conversation_id, user_id=None)
        if conversation:
            conversation.updated_at = datetime.now(UTC)
            self.session.add(conversation)

        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_messages(self, conversation_id: int, *, limit: int = 50) -> List[Message]:
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_last_message(self, conversation_id: int) -> Optional[Message]:
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_conversation(self, conversation_id: int, *, user_id: Optional[UUID]) -> bool:
        conversation = await self.get_conversation(conversation_id, user_id=user_id)
        if not conversation:
            return False
        await self.session.delete(conversation)
        await self.session.commit()
        return True
