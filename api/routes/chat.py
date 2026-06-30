"""FastAPI routes for platform chat agent threads and messages."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, AsyncIterator

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from api.agent.graph import ainvoke_agent
from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    ChatMessageDTO,
    ChatThreadDTO,
    CreateThreadRequest,
    DeleteThreadResponse,
    SendMessageRequest,
    SendMessageResponse,
    ThreadDetailResponse,
)
from db import chat_store
from observability.logger import log_llm_call

router = APIRouter(tags=["chat"])

_CONVERSATION_ROLES = frozenset({"user", "assistant"})
_TITLE_MODEL = "claude-haiku-4-5-20251001"
_TITLE_SYSTEM_PROMPT = (
    "Generate a 3-6 word title for this chat thread. Return only the title, nothing else."
)


def _thread_or_404(thread_id: str, access_token: str):
    thread = chat_store.get_thread(thread_id, access_token)
    if thread is None:
        raise HTTPException(
            status_code=404,
            detail=f"Chat thread '{thread_id}' not found.",
        )
    return thread


def _conversation_history(thread_id: str, access_token: str) -> list[dict[str, str]]:
    """Build message list for the agent from persisted thread history."""
    return [
        {"role": message.role, "content": message.content}
        for message in chat_store.list_messages(thread_id, access_token)
        if message.role in _CONVERSATION_ROLES
    ]


def _normalize_thread_title(raw_title: str) -> str:
    """Strip quotes/whitespace and cap length for sidebar display."""
    title = raw_title.strip().strip('"\'')
    if len(title) > 80:
        title = title[:77].rstrip() + "..."
    return title


async def _generate_thread_title(
    first_message: str,
    *,
    session_id: str | None = None,
) -> str | None:
    """Generate a short thread title from the user's first message."""
    client = anthropic.AsyncAnthropic()
    t0 = time.perf_counter()
    try:
        response = await client.messages.create(
            model=_TITLE_MODEL,
            max_tokens=20,
            system=_TITLE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": first_message}],
        )
    except anthropic.APIError as exc:
        log_llm_call(
            app_name="platform_agent",
            tool_name="generate_thread_title",
            model=_TITLE_MODEL,
            tokens_in=None,
            tokens_out=None,
            latency_seconds=time.perf_counter() - t0,
            rag_used=False,
            error=str(exc),
            session_id=session_id,
        )
        return None

    log_llm_call(
        app_name="platform_agent",
        tool_name="generate_thread_title",
        model=_TITLE_MODEL,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        latency_seconds=time.perf_counter() - t0,
        rag_used=False,
        session_id=session_id,
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    if not text:
        return None
    return _normalize_thread_title(text) or None


async def _run_agent_turn(
    thread_id: str,
    content: str,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Run one agent turn and return the response payload."""
    thread = _thread_or_404(thread_id, current_user.access_token)

    stripped = content.strip()
    if not stripped:
        raise HTTPException(status_code=422, detail="Message content cannot be empty.")

    messages = _conversation_history(thread_id, current_user.access_token)
    needs_title = not (thread.title and thread.title.strip()) and not messages
    messages.append({"role": "user", "content": stripped})

    result = await ainvoke_agent(
        messages=messages,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
        thread_id=thread_id,
    )

    new_title: str | None = None
    if needs_title:
        generated_title = await _generate_thread_title(
            stripped,
            session_id=thread_id,
        )
        if generated_title:
            chat_store.update_thread_title(
                thread_id,
                generated_title,
                access_token=current_user.access_token,
            )
            new_title = generated_title

    return {
        "thread_id": thread_id,
        "content": result.get("assistant_content", ""),
        "suggestions": result.get("suggestions") or [],
        "module_launch": result.get("module_launch"),
        "title": new_title,
    }


def _format_sse_event(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _split_content_chunks(content: str) -> list[str]:
    """Split assistant content into word-sized chunks for streaming."""
    if not content:
        return []
    parts = re.split(r"(\s+)", content)
    chunks: list[str] = []
    for index, part in enumerate(parts):
        if not part:
            continue
        if index % 2 == 1:
            if chunks:
                chunks[-1] += part
            else:
                chunks.append(part)
        else:
            chunks.append(part)
    return chunks


async def _event_stream(result: dict[str, Any]) -> AsyncIterator[str]:
    """Yield SSE frames: content chunks, then metadata, then done."""
    content = result.get("content", "")
    for chunk in _split_content_chunks(content):
        yield _format_sse_event("chunk", {"text": chunk})
        await asyncio.sleep(0.02)

    yield _format_sse_event(
        "meta",
        {
            "thread_id": result.get("thread_id"),
            "suggestions": result.get("suggestions") or [],
            "module_launch": result.get("module_launch"),
            "title": result.get("title"),
        },
    )
    yield _format_sse_event("done", {})


@router.post("/api/chat/threads", response_model=ChatThreadDTO)
def create_thread(
    request: CreateThreadRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ChatThreadDTO:
    thread_id = chat_store.create_thread(
        user_id=current_user.user_id,
        access_token=current_user.access_token,
        org_id=request.org_id,
        title=request.title,
    )
    thread = chat_store.get_thread(thread_id, current_user.access_token)
    if thread is None:
        raise HTTPException(status_code=500, detail="Failed to create chat thread.")
    return ChatThreadDTO.from_domain(thread)


@router.get("/api/chat/threads", response_model=list[ChatThreadDTO])
def list_threads(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[ChatThreadDTO]:
    threads = chat_store.list_threads(current_user.access_token)
    return [ChatThreadDTO.from_domain(thread) for thread in threads]


@router.get("/api/chat/threads/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(
    thread_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> ThreadDetailResponse:
    thread = _thread_or_404(thread_id, current_user.access_token)
    messages = chat_store.list_messages(thread_id, current_user.access_token)
    return ThreadDetailResponse(
        thread=ChatThreadDTO.from_domain(thread),
        messages=[ChatMessageDTO.from_domain(message) for message in messages],
    )


@router.post(
    "/api/chat/threads/{thread_id}/messages",
    response_model=SendMessageResponse,
)
async def send_message(
    thread_id: str,
    request: SendMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SendMessageResponse:
    result = await _run_agent_turn(thread_id, request.content, current_user)
    return SendMessageResponse(**result)


@router.post("/api/chat/threads/{thread_id}/messages/stream")
async def send_message_stream(
    thread_id: str,
    request: SendMessageRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    result = await _run_agent_turn(thread_id, request.content, current_user)
    return StreamingResponse(
        _event_stream(result),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/api/chat/threads/{thread_id}", response_model=DeleteThreadResponse)
def delete_thread(
    thread_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> DeleteThreadResponse:
    _thread_or_404(thread_id, current_user.access_token)
    chat_store.delete_thread(thread_id, access_token=current_user.access_token)
    return DeleteThreadResponse(deleted=True)
