"""Supabase CRUD for platform chat agent threads and messages.

Tables (managed by supabase/migrations/):
  chat_threads   — user-owned conversation threads
  chat_messages  — messages scoped to a thread

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from db.client import get_user_client

_THREAD_COLUMNS = (
    "thread_id, user_id, org_id, title, created_at, updated_at, deleted_at"
)
_MESSAGE_COLUMNS = (
    "message_id, thread_id, role, content, metadata, created_at"
)


@dataclass
class ChatThread:
    thread_id: str
    user_id: str
    org_id: str | None
    title: str | None
    created_at: str
    updated_at: str
    deleted_at: str | None = None


@dataclass
class ChatMessage:
    message_id: str
    thread_id: str
    role: str
    content: str
    metadata: dict[str, Any]
    created_at: str


def create_thread(
    *,
    user_id: str,
    access_token: str,
    org_id: str | None = None,
    title: str | None = None,
) -> str:
    """Insert a new chat thread and return its thread_id."""
    client = get_user_client(access_token)
    now = _utc_now_iso()
    payload: dict[str, Any] = {
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
    }
    if org_id is not None:
        payload["org_id"] = org_id
    if title is not None:
        payload["title"] = title.strip() if title else None

    response = client.table("chat_threads").insert(payload).execute()
    return str(response.data[0]["thread_id"])


def list_threads(access_token: str) -> list[ChatThread]:
    """Return non-deleted threads for the authenticated user, newest activity first."""
    client = get_user_client(access_token)
    response = (
        client.table("chat_threads")
        .select(_THREAD_COLUMNS)
        .is_("deleted_at", "null")
        .order("updated_at", desc=True)
        .execute()
    )
    return [_thread_from_row(row) for row in response.data]


def get_thread(thread_id: str, access_token: str) -> ChatThread | None:
    """Return a single non-deleted thread by ID, or None if not found / not owned."""
    client = get_user_client(access_token)
    response = (
        client.table("chat_threads")
        .select(_THREAD_COLUMNS)
        .eq("thread_id", thread_id)
        .is_("deleted_at", "null")
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _thread_from_row(response.data[0])


def update_thread_title(thread_id: str, title: str, *, access_token: str) -> None:
    """Set the thread title and bump updated_at."""
    client = get_user_client(access_token)
    client.table("chat_threads").update(
        {
            "title": title.strip() if title else None,
            "updated_at": _utc_now_iso(),
        }
    ).eq("thread_id", thread_id).execute()


def touch_thread(thread_id: str, *, access_token: str) -> None:
    """Bump updated_at on a thread (e.g. after a new message)."""
    client = get_user_client(access_token)
    client.table("chat_threads").update({"updated_at": _utc_now_iso()}).eq(
        "thread_id", thread_id
    ).execute()


def delete_thread(thread_id: str, *, access_token: str) -> None:
    """Soft-delete a thread by setting deleted_at."""
    client = get_user_client(access_token)
    client.table("chat_threads").update(
        {
            "deleted_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
    ).eq("thread_id", thread_id).execute()


def create_message(
    thread_id: str,
    role: str,
    content: str,
    *,
    access_token: str,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Insert a message into a thread and return its message_id."""
    client = get_user_client(access_token)
    response = (
        client.table("chat_messages")
        .insert(
            {
                "thread_id": thread_id,
                "role": role,
                "content": content,
                "metadata": metadata or {},
            }
        )
        .execute()
    )
    return str(response.data[0]["message_id"])


def list_messages(thread_id: str, access_token: str) -> list[ChatMessage]:
    """Return all messages for a thread in chronological order."""
    client = get_user_client(access_token)
    response = (
        client.table("chat_messages")
        .select(_MESSAGE_COLUMNS)
        .eq("thread_id", thread_id)
        .order("created_at", desc=False)
        .execute()
    )
    return [_message_from_row(row) for row in response.data]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _thread_from_row(row: dict) -> ChatThread:
    org_id = row.get("org_id")
    title = row.get("title")
    deleted_at = row.get("deleted_at")
    return ChatThread(
        thread_id=str(row["thread_id"]),
        user_id=str(row["user_id"]),
        org_id=str(org_id) if org_id is not None else None,
        title=str(title) if title is not None else None,
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
        deleted_at=str(deleted_at) if deleted_at is not None else None,
    )


def _message_from_row(row: dict) -> ChatMessage:
    raw_metadata = row.get("metadata")
    metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
    return ChatMessage(
        message_id=str(row["message_id"]),
        thread_id=str(row["thread_id"]),
        role=row["role"],
        content=row["content"],
        metadata=metadata,
        created_at=str(row.get("created_at", "")),
    )
