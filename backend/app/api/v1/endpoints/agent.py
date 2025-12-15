"""Agent chat endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import StreamingResponse

from app.api import deps
from app.schemas.agent import (
    ChatMessageRequest,
    ChatResponse,
    ConversationListResponse,
    MessageListResponse,
)
from app.services.agent import AgentService
from app.models.users import User

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    payload: ChatMessageRequest,
    service: AgentService = Depends(deps.get_agent_service),
    user: User | None = Depends(deps.get_optional_current_user),
) -> ChatResponse:
    """Send a message to the agent and receive streamed responses."""

    user_id = user.id if user else None
    return await service.send_message(
        content=payload.content,
        conversation_id=payload.conversation_id,
        user_id=user_id,
    )


@router.post("/chat/stream")
async def chat_with_agent_stream(
    payload: ChatMessageRequest,
    service: AgentService = Depends(deps.get_agent_service),
    user: User | None = Depends(deps.get_optional_current_user),
):
    """Send a message to the agent and receive Server-Sent Events for streaming UI updates."""

    user_id = user.id if user else None
    event_stream = service.stream_message(
        content=payload.content,
        conversation_id=payload.conversation_id,
        user_id=user_id,
    )
    return StreamingResponse(event_stream, media_type="text/event-stream")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    service: AgentService = Depends(deps.get_agent_service),
    user: User | None = Depends(deps.get_optional_current_user),
) -> ConversationListResponse:
    """List recent conversations for the current user (or anonymous)."""

    user_id = user.id if user else None
    return await service.list_conversations(user_id=user_id)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
async def list_conversation_messages(
    conversation_id: int,
    service: AgentService = Depends(deps.get_agent_service),
    user: User | None = Depends(deps.get_optional_current_user),
) -> MessageListResponse:
    """Load the messages for a specific conversation."""

    user_id = user.id if user else None
    return await service.list_messages(conversation_id, user_id=user_id)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    service: AgentService = Depends(deps.get_agent_service),
    user: User | None = Depends(deps.get_optional_current_user),
) -> Response:
    user_id = user.id if user else None
    await service.delete_conversation(conversation_id, user_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
