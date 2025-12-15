from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.models.agent import Message
from app.services.agent import AgentService


def test_to_langchain_messages_merges_text_and_tool_calls() -> None:
    service = AgentService.__new__(AgentService)

    history = [
        Message(id=1, conversation_id=1, role="user", content="介绍北邮最新信息"),
        # Persisted assistant pre-tool text (no tool fields)
        Message(id=2, conversation_id=1, role="assistant", content="我来为您搜索北京邮电大学的最新信息。"),
        # Persisted tool calls as separate assistant records with empty content
        Message(
            id=3,
            conversation_id=1,
            role="assistant",
            content="",
            tool_name="search_xhs_posts",
            tool_call_id="call-1",
            tool_args={"query": "北京邮电大学 最新", "limit": 5},
        ),
        Message(
            id=4,
            conversation_id=1,
            role="assistant",
            content="",
            tool_name="search_xhs_posts",
            tool_call_id="call-2",
            tool_args={"query": "北邮 校园生活", "limit": 5},
        ),
        Message(
            id=5,
            conversation_id=1,
            role="tool",
            content="result payload",
            tool_name="search_xhs_posts",
            tool_call_id="call-1",
        ),
        Message(id=6, conversation_id=1, role="assistant", content="综合来看，以下是要点……"),
    ]

    lc = service._to_langchain_messages(history)

    assert isinstance(lc[0], SystemMessage)
    assert isinstance(lc[1], HumanMessage)

    merged = lc[2]
    assert isinstance(merged, AIMessage)
    assert merged.content == "我来为您搜索北京邮电大学的最新信息。"
    assert merged.tool_calls
    assert len(merged.tool_calls) == 2
    assert merged.tool_calls[0]["id"] == "call-1"
    assert merged.tool_calls[1]["id"] == "call-2"

    assert any(isinstance(m, ToolMessage) for m in lc)
