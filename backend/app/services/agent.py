"""LangChain-powered agent service with chat history and tools."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, Iterable, List, Optional
from uuid import UUID

from fastapi import HTTPException
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.models.agent import Conversation, Message
from app.repositories.agent import AgentRepository
from app.schemas.agent import ChatResponse, ChatMessage, MessageListResponse, ConversationListResponse
from app.services.xhs_search import XhsSearchService


SYSTEM_PROMPT = """
You are a travel assistant for a tourism website. Be concise and actionable.
When searching for travel inspiration, itineraries, or recommendations, prefer calling the XiaoHongShu search tool.
Summarize results briefly and cite URLs when available. Keep answers in Chinese when the user uses Chinese.
""".strip()


class AgentService:
    """Coordinate chat, history persistence, and tool execution."""

    def __init__(self, repo: AgentRepository, xhs_search: XhsSearchService):
        if not settings.ai_api_key:
            raise RuntimeError("AI API key is not configured (settings.ai_api_key)")

        self.repo = repo
        self.xhs_search = xhs_search

        llm_kwargs = {
            "model": settings.ai_model,
            "api_key": settings.ai_api_key,
            "base_url": settings.ai_api_base,
            "temperature": 0.3,
        }
        self.llm = ChatOpenAI(**llm_kwargs)
        self.llm_stream = ChatOpenAI(streaming=True, **llm_kwargs)
        self.xhs_tool = self._build_xhs_tool()
        self.llm_with_tools = self.llm.bind_tools([self.xhs_tool])
        self.llm_stream_with_tools = self.llm_stream.bind_tools([self.xhs_tool])

    async def send_message(
        self,
        *,
        content: str,
        conversation_id: Optional[int],
        user_id: Optional[UUID],
    ) -> ChatResponse:
        conversation = await self._ensure_conversation(conversation_id, user_id, content)

        # Defensive: SQLModel IDs are Optional in type-checking, but for persisted rows
        # the ID must exist. Raise early if something is off.
        if conversation.id is None:  # pragma: no cover
            raise RuntimeError("Conversation has no id")

        user_msg = await self.repo.add_message(
            conversation_id=conversation.id,
            role="user",
            content=content,
        )

        history = await self.repo.list_messages(conversation.id, limit=60)
        lc_messages = self._to_langchain_messages(history)

        collected: List[Message] = [user_msg]
        ai_msg = await self.llm_with_tools.ainvoke(lc_messages)
        collected.extend(await self._persist_ai_message(conversation.id, ai_msg))

        # Some models may interleave: text -> tool -> text -> tool -> ... within one overall reply.
        # Loop until no tool calls (or we hit a safety cap).
        max_tool_rounds = 8
        rounds = 0
        working_lc = list(lc_messages)
        while ai_msg.tool_calls:
            if rounds >= max_tool_rounds:
                raise RuntimeError("Exceeded maximum tool-call rounds")
            rounds += 1
            tool_messages, stored_tool, _ = await self._run_tools(conversation.id, ai_msg)
            collected.extend(stored_tool)
            working_lc = working_lc + [ai_msg, *tool_messages]
            ai_msg = await self.llm_with_tools.ainvoke(working_lc)
            collected.extend(await self._persist_ai_message(conversation.id, ai_msg))

        return ChatResponse(
            conversation_id=conversation.id,
            messages=[ChatMessage.model_validate(msg) for msg in collected],
        )

    async def stream_message(
        self,
        *,
        content: str,
        conversation_id: Optional[int],
        user_id: Optional[UUID],
    ) -> AsyncIterator[str]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def send_event(payload: dict, event: Optional[str] = None) -> None:
            await queue.put(self._format_sse(payload, event))

        async def send_delta(delta: str) -> None:
            if delta:
                await send_event({"type": "delta", "delta": delta})

        async def runner() -> None:
            try:
                conversation = await self._ensure_conversation(conversation_id, user_id, content)
                if conversation.id is None:  # pragma: no cover
                    raise RuntimeError("Conversation has no id")
                await send_event({"type": "conversation", "conversation_id": conversation.id})

                user_msg = await self.repo.add_message(
                    conversation_id=conversation.id,
                    role="user",
                    content=content,
                )
                await send_event({"type": "message", "message": self._serialize_message(user_msg)})

                history = await self.repo.list_messages(conversation.id, limit=60)
                lc_messages = self._to_langchain_messages(history)

                working_lc = list(lc_messages)
                ai_msg, stored_ai = await self._stream_and_store_messages(
                    working_lc,
                    conversation.id,
                    send_delta,
                )
                for msg in stored_ai:
                    await send_event({"type": "message", "message": self._serialize_message(msg)})

                max_tool_rounds = 8
                rounds = 0
                while ai_msg.tool_calls:
                    if rounds >= max_tool_rounds:
                        await send_event({"type": "error", "message": "Exceeded maximum tool-call rounds"})
                        break
                    rounds += 1

                    for call in ai_msg.tool_calls:
                        await send_event(
                            {
                                "type": "status",
                                "conversation_id": conversation.id,
                                "status": "tool_call_started",
                                "label": f"{call.get('name') or '工具'} 调用中",
                                "tool_name": call.get("name"),
                                "tool_call_id": call.get("id"),
                                "tool_args": call.get("args"),
                            }
                        )

                    tool_langchain_msgs, stored_tool, tool_statuses = await self._run_tools(conversation.id, ai_msg)
                    for msg in stored_tool:
                        await send_event({"type": "message", "message": self._serialize_message(msg)})
                    for status in tool_statuses:
                        await send_event(
                            {
                                "type": "status",
                                "conversation_id": conversation.id,
                                "status": status["status"],
                                "label": status["label"],
                                "tool_name": status.get("tool_name"),
                                "tool_call_id": status.get("tool_call_id"),
                                "tool_args": status.get("tool_args"),
                                "tool_output_preview": status.get("tool_output_preview"),
                                "message": status.get("message"),
                            }
                        )

                    working_lc = working_lc + [ai_msg, *tool_langchain_msgs]
                    ai_msg, stored_ai = await self._stream_and_store_messages(
                        working_lc,
                        conversation.id,
                        send_delta,
                    )
                    for msg in stored_ai:
                        await send_event({"type": "message", "message": self._serialize_message(msg)})
                await send_event({"type": "done"})
            except Exception as exc:  # pragma: no cover - surfaced to client
                await send_event({"type": "error", "message": str(exc)})
            finally:
                await queue.put(None)

        asyncio.create_task(runner())

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item

    async def list_conversations(self, *, user_id: Optional[UUID]) -> ConversationListResponse:
        conversations = await self.repo.list_conversations(user_id=user_id, limit=30)
        items: List[dict] = []
        for conv in conversations:
            last_msg = await self.repo.get_last_message(conv.id)
            preview = (last_msg.content[:120] if last_msg and last_msg.content else None)
            items.append(
                {
                    "id": conv.id,
                    "title": conv.title,
                    "summary": conv.summary,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                    "last_message_preview": preview,
                }
            )
        return ConversationListResponse(items=items)

    async def list_messages(self, conversation_id: int, *, user_id: Optional[UUID]) -> MessageListResponse:
        conversation = await self.repo.get_conversation(conversation_id, user_id=user_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = await self.repo.list_messages(conversation_id, limit=200)
        return MessageListResponse(items=[ChatMessage.model_validate(m) for m in messages])

    async def delete_conversation(self, conversation_id: int, *, user_id: Optional[UUID]) -> None:
        deleted = await self.repo.delete_conversation(conversation_id, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")

    async def _ensure_conversation(
        self,
        conversation_id: Optional[int],
        user_id: Optional[UUID],
        title_source: str,
    ) -> Conversation:
        if conversation_id:
            existing = await self.repo.get_conversation(conversation_id, user_id=user_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return existing

        safe_title = (title_source or "New chat").strip()
        if len(safe_title) > 80:
            safe_title = safe_title[:80]
        return await self.repo.create_conversation(title=safe_title or "New chat", user_id=user_id)

    async def _persist_ai_message(self, conversation_id: int, ai_msg: AIMessage) -> List[Message]:
        stored: List[Message] = []
        text_content = self._stringify_content(ai_msg.content)

        # Important: when the model outputs text and then issues tool calls in the same assistant turn,
        # persist the human-visible text as a normal assistant message (no tool fields). Otherwise,
        # UIs that treat tool-call messages specially may hide/overwrite the content.
        if ai_msg.tool_calls:
            if text_content.strip():
                stored.append(
                    await self.repo.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=text_content,
                    )
                )
            for call in ai_msg.tool_calls:
                stored.append(
                    await self.repo.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        # Keep tool-call records text-free to avoid duplicating/hiding the pre-tool output.
                        content="",
                        tool_name=call["name"],
                        tool_call_id=call.get("id"),
                        tool_args=call.get("args"),
                    )
                )
            return stored

        stored.append(
            await self.repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=text_content,
            )
        )
        return stored

    async def _run_tools(
        self,
        conversation_id: int,
        ai_msg: AIMessage,
    ) -> tuple[List[ToolMessage], List[Message], List[dict[str, Any]]]:
        tool_messages: List[ToolMessage] = []
        stored: List[Message] = []
        results_meta: List[dict[str, Any]] = []
        for call in ai_msg.tool_calls or []:
            args = call.get("args") or {}
            name = call.get("name") or ""
            call_id = call.get("id") or f"tool-{conversation_id}-{len(tool_messages)}"
            status_message: Optional[str] = None
            status_state = "tool_call_completed"
            status_label = f"{name or '工具'} 完成"
            try:
                result = await self.xhs_tool.ainvoke(args)
            except Exception as exc:  # pragma: no cover - tool errors surfaced to model
                message = str(exc)
                result = {"error": message}
                status_message = message
                status_state = "tool_call_failed"
                status_label = f"{name or '工具'} 失败"
            stored_msg = await self.repo.add_message(
                conversation_id=conversation_id,
                role="tool",
                content=self._stringify_content(result),
                tool_name=name,
                tool_call_id=call_id,
                tool_args=args,
                tool_output=result if isinstance(result, dict) else {"result": result},
            )
            stored.append(stored_msg)
            tool_messages.append(ToolMessage(content=self._stringify_content(result), name=name, tool_call_id=call_id))
            results_meta.append(
                {
                    "tool_call_id": call_id,
                    "tool_name": name,
                    "tool_args": args,
                    "status": status_state,
                    "label": status_label,
                    "message": status_message,
                    "tool_output_preview": self._summarize_tool_output(result),
                }
            )
        return tool_messages, stored, results_meta

    async def _stream_and_store_messages(
        self,
        messages: List[SystemMessage | HumanMessage | AIMessage | ToolMessage],
        conversation_id: int,
        send_delta: Callable[[str], Awaitable[None]],
    ) -> tuple[AIMessage, List[Message]]:
        ai_msg = await self._stream_llm_messages(messages, send_delta)
        stored = await self._persist_ai_message(conversation_id, ai_msg)
        return ai_msg, stored

    async def _stream_llm_messages(
        self,
        messages: List[SystemMessage | HumanMessage | AIMessage | ToolMessage],
        send_delta: Callable[[str], Awaitable[None]],
    ) -> AIMessage:
        ai_msg: Optional[AIMessage] = None
        async for event in self.llm_stream_with_tools.astream_events(messages, version="v1"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                chunk: AIMessageChunk = event["data"]["chunk"]
                delta = self._chunk_to_text(chunk)
                if delta:
                    await send_delta(delta)
            elif kind == "on_chat_model_end":
                ai_msg = event["data"]["output"]
        if ai_msg is None:  # pragma: no cover - defensive
            raise RuntimeError("LLM stream produced no output")
        return ai_msg

    @staticmethod
    def _chunk_to_text(chunk: AIMessageChunk) -> str:
        content = chunk.content
        if isinstance(content, str):
            return content
        parts: List[str] = []
        for item in content or []:
            item_type = getattr(item, "type", None)
            if item_type == "text":
                parts.append(getattr(item, "text", ""))
        return "".join(parts)

    @staticmethod
    def _serialize_message(message: Message) -> dict:
        return ChatMessage.model_validate(message).model_dump(mode="json")

    @staticmethod
    def _format_sse(payload: dict, event: Optional[str] = None) -> str:
        body = json.dumps(payload, ensure_ascii=False)
        if event:
            return f"event: {event}\ndata: {body}\n\n"
        return f"data: {body}\n\n"

    def _to_langchain_messages(self, history: Iterable[Message]) -> List[SystemMessage | HumanMessage | AIMessage | ToolMessage]:
        # We sometimes persist an assistant turn as:
        # 1) assistant(text)
        # 2) assistant(tool_call, empty text)
        # to keep UI from losing the pre-tool text. When rebuilding history for the model,
        # merge consecutive (assistant text) + (assistant tool_call...) back into one AIMessage.
        items = list(history)
        lc: List[SystemMessage | HumanMessage | AIMessage | ToolMessage] = [SystemMessage(content=SYSTEM_PROMPT)]

        i = 0
        while i < len(items):
            msg = items[i]
            if msg.role == "user":
                lc.append(HumanMessage(content=msg.content))
                i += 1
                continue

            if msg.role == "assistant" and (not msg.tool_name):
                tool_calls: List[dict[str, Any]] = []
                j = i + 1
                while j < len(items):
                    next_msg = items[j]
                    if (
                        next_msg.role == "assistant"
                        and next_msg.tool_name
                        and next_msg.tool_args is not None
                        and (next_msg.content or "") == ""
                    ):
                        tool_calls.append(
                            {
                                "name": next_msg.tool_name,
                                "args": next_msg.tool_args,
                                "id": next_msg.tool_call_id or f"call-{next_msg.id}",
                            }
                        )
                        j += 1
                        continue
                    break

                if tool_calls:
                    lc.append(AIMessage(content=msg.content or "", tool_calls=tool_calls))
                    i = j
                    continue

                lc.append(AIMessage(content=msg.content))
                i += 1
                continue

            if msg.role == "assistant" and msg.tool_name and msg.tool_args is not None:
                lc.append(
                    AIMessage(
                        content=msg.content or "",
                        tool_calls=[
                            {
                                "name": msg.tool_name,
                                "args": msg.tool_args,
                                "id": msg.tool_call_id or f"call-{msg.id}",
                            }
                        ],
                    )
                )
                i += 1
                continue

            if msg.role == "assistant":
                lc.append(AIMessage(content=msg.content))
                i += 1
                continue

            if msg.role == "tool":
                lc.append(
                    ToolMessage(
                        content=msg.content,
                        name=msg.tool_name or "tool",
                        tool_call_id=msg.tool_call_id or f"call-{msg.id}",
                    )
                )
                i += 1
                continue

            i += 1

        return lc

    def _stringify_content(self, content: object) -> str:
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)

    def _summarize_tool_output(self, result: object) -> Optional[str]:
        if result is None:
            return None
        if isinstance(result, str):
            text = result.strip()
        else:
            try:
                text = json.dumps(result, ensure_ascii=False)
            except Exception:
                text = str(result)
            text = text.strip()
        if not text:
            return None
        text = text.replace("\n", " ")
        return text[:160]

    def _build_xhs_tool(self):
        @tool("search_xhs_posts", return_direct=False)
        async def search_xhs_posts(query: str, limit: int = 5) -> str:
            """Search XiaoHongShu posts about destinations, itineraries, or tips."""
            results = await self.xhs_search.search_notes(query, limit=limit)
            if not results:
                return "未找到相关结果"
            lines = []
            for item in results:
                title = item.get("title") or "相关笔记"
                meta: List[str] = []
                if item.get("author"):
                    meta.append(f"作者: {item['author']}")
                if item.get("liked_count"):
                    meta.append(f"点赞: {item['liked_count']}")
                body = (item.get("desc") or "").strip()
                body_text = body if body else "暂无正文"
                if len(body_text) > 400:
                    body_text = f"{body_text[:400]}..."
                entry_lines = [f"- {title}", f"  正文: {body_text}"]
                if meta:
                    entry_lines.append(f"  元信息: {' | '.join(meta)}")
                lines.append("\n".join(entry_lines))
            return "\n".join(lines)

        return search_xhs_posts
