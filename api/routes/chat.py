"""FastAPI routes for platform chat agent threads and messages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.agent.graph import ainvoke_agent
from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    ChatThreadDTO,
    CreateThreadRequest,
    DeleteThreadResponse,
    SendMessageRequest,
    SendMessageResponse,
    ThreadDetailResponse,
    ChatMessageDTO,
)
from db import chat_store

router = APIRouter(tags=["chat"])

_CONVERSATION_ROLES = frozenset({"user", "assistant"})


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
    _thread_or_404(thread_id, current_user.access_token)

    content = request.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content cannot be empty.")

    messages = _conversation_history(thread_id, current_user.access_token)
    messages.append({"role": "user", "content": content})

    result = await ainvoke_agent(
        messages=messages,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
        thread_id=thread_id,
    )

    return SendMessageResponse(
        thread_id=thread_id,
        content=result.get("assistant_content", ""),
        suggestions=result.get("suggestions") or [],
        module_launch=result.get("module_launch"),
    )


@router.delete("/api/chat/threads/{thread_id}", response_model=DeleteThreadResponse)
def delete_thread(
    thread_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> DeleteThreadResponse:
    _thread_or_404(thread_id, current_user.access_token)
    chat_store.delete_thread(thread_id, access_token=current_user.access_token)
    return DeleteThreadResponse(deleted=True)
