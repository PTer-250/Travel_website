from __future__ import annotations

from typing import Any, Optional

import pytest
from langchain_core.messages import AIMessage

from app.models.agent import Conversation, Message
from app.schemas.agent import ChatResponse
from app.services.agent import AgentService


class _FakeTool:
    async def ainvoke(self, args: dict) -> str:
        query = args.get("query", "")
        return f"tool_result_for:{query}"


class _FakeLLM:
    def __init__(self, outputs: list[AIMessage]):
        self._outputs = outputs
        self.calls: list[list[Any]] = []

    async def ainvoke(self, messages: list[Any]) -> AIMessage:
        self.calls.append(messages)
        if not self._outputs:
            raise RuntimeError("No more fake outputs")
        return self._outputs.pop(0)


class _FakeRepo:
    def __init__(self) -> None:
        self._conversation: Optional[Conversation] = None
        self._messages: list[Message] = []
        self._next_id = 1

    async def create_conversation(self, *, title: str, user_id) -> Conversation:
        self._conversation = Conversation(id=1, title=title, user_id=user_id)
        return self._conversation

    async def get_conversation(self, conversation_id: int, *, user_id) -> Optional[Conversation]:
        if self._conversation and self._conversation.id == conversation_id:
            return self._conversation
        return None

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
        msg = Message(
            id=self._next_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tool_args=tool_args,
            tool_output=tool_output,
        )
        self._next_id += 1
        self._messages.append(msg)
        return msg

    async def list_messages(self, conversation_id: int, *, limit: int = 50) -> list[Message]:
        return [m for m in self._messages if m.conversation_id == conversation_id][-limit:]


@pytest.mark.asyncio
async def test_send_message_supports_multiple_tool_rounds() -> None:
    repo = _FakeRepo()
    service = AgentService.__new__(AgentService)
    service.repo = repo
    service.xhs_tool = _FakeTool()

    # Simulate: assistant(text+tool1) -> assistant(text+tool2) -> assistant(final)
    service.llm_with_tools = _FakeLLM(
        [
            AIMessage(
                content="先输出一段，然后调用工具1。",
                tool_calls=[{"name": "search_xhs_posts", "args": {"query": "q1", "limit": 5}, "id": "call-1"}],
            ),
            AIMessage(
                content="工具1结束后再输出，再调用工具2。",
                tool_calls=[{"name": "search_xhs_posts", "args": {"query": "q2", "limit": 5}, "id": "call-2"}],
            ),
            AIMessage(content="全部完成。"),
        ]
    )

    resp: ChatResponse = await service.send_message(content="hi", conversation_id=None, user_id=None)

    assert resp.conversation_id == 1
    contents = [m.content for m in resp.messages]

    assert any("先输出一段" in c for c in contents)
    assert any("工具1结束后" in c for c in contents)
    assert any("全部完成" in c for c in contents)

    # Ensure both tool results were persisted as tool-role messages
    tool_msgs = [m for m in resp.messages if m.role == "tool"]
    assert len(tool_msgs) == 2
    assert "tool_result_for:q1" in tool_msgs[0].content
    assert "tool_result_for:q2" in tool_msgs[1].content
