"""Supabase CRUD for platform chat agent semantic memory.

Tables (managed by supabase/migrations/):
  user_memory — user-level preferences and focus areas
  org_memory  — org-level shared context

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from db.client import get_user_client

_USER_MEMORY_COLUMNS = (
    "memory_id, user_id, content, category, created_at, updated_at"
)
_ORG_MEMORY_COLUMNS = (
    "memory_id, org_id, created_by, content, category, created_at, updated_at"
)


@dataclass
class UserMemory:
    memory_id: str
    user_id: str
    content: str
    category: str
    created_at: str
    updated_at: str


@dataclass
class OrgMemory:
    memory_id: str
    org_id: str
    created_by: str
    content: str
    category: str
    created_at: str
    updated_at: str


def create_user_memory(
    content: str,
    category: str,
    *,
    user_id: str,
    access_token: str,
) -> str:
    """Insert a user memory entry and return its memory_id."""
    client = get_user_client(access_token)
    now = _utc_now_iso()
    response = (
        client.table("user_memory")
        .insert(
            {
                "user_id": user_id,
                "content": content.strip(),
                "category": category.strip(),
                "created_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )
    return str(response.data[0]["memory_id"])


def list_user_memory(access_token: str) -> list[UserMemory]:
    """Return all memory entries for the authenticated user."""
    client = get_user_client(access_token)
    response = (
        client.table("user_memory")
        .select(_USER_MEMORY_COLUMNS)
        .order("updated_at", desc=True)
        .execute()
    )
    return [_user_memory_from_row(row) for row in response.data]


def update_user_memory(memory_id: str, *, access_token: str, **fields) -> None:
    """Update content and/or category on a user memory entry."""
    allowed = {"content", "category"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    if "content" in updates and isinstance(updates["content"], str):
        updates["content"] = updates["content"].strip()
    if "category" in updates and isinstance(updates["category"], str):
        updates["category"] = updates["category"].strip()
    updates["updated_at"] = _utc_now_iso()
    client = get_user_client(access_token)
    client.table("user_memory").update(updates).eq("memory_id", memory_id).execute()


def delete_user_memory(memory_id: str, *, access_token: str) -> None:
    """Hard-delete a user memory entry."""
    client = get_user_client(access_token)
    client.table("user_memory").delete().eq("memory_id", memory_id).execute()


def create_org_memory(
    org_id: str,
    content: str,
    category: str,
    *,
    created_by: str,
    access_token: str,
) -> str:
    """Insert an org memory entry and return its memory_id."""
    client = get_user_client(access_token)
    now = _utc_now_iso()
    response = (
        client.table("org_memory")
        .insert(
            {
                "org_id": org_id,
                "created_by": created_by,
                "content": content.strip(),
                "category": category.strip(),
                "created_at": now,
                "updated_at": now,
            }
        )
        .execute()
    )
    return str(response.data[0]["memory_id"])


def list_org_memory(org_id: str, access_token: str) -> list[OrgMemory]:
    """Return all memory entries for an organization."""
    client = get_user_client(access_token)
    response = (
        client.table("org_memory")
        .select(_ORG_MEMORY_COLUMNS)
        .eq("org_id", org_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return [_org_memory_from_row(row) for row in response.data]


def update_org_memory(memory_id: str, *, access_token: str, **fields) -> None:
    """Update content and/or category on an org memory entry."""
    allowed = {"content", "category"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    if "content" in updates and isinstance(updates["content"], str):
        updates["content"] = updates["content"].strip()
    if "category" in updates and isinstance(updates["category"], str):
        updates["category"] = updates["category"].strip()
    updates["updated_at"] = _utc_now_iso()
    client = get_user_client(access_token)
    client.table("org_memory").update(updates).eq("memory_id", memory_id).execute()


def delete_org_memory(memory_id: str, *, access_token: str) -> None:
    """Hard-delete an org memory entry."""
    client = get_user_client(access_token)
    client.table("org_memory").delete().eq("memory_id", memory_id).execute()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_memory_from_row(row: dict) -> UserMemory:
    return UserMemory(
        memory_id=str(row["memory_id"]),
        user_id=str(row["user_id"]),
        content=row["content"],
        category=row["category"],
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
    )


def _org_memory_from_row(row: dict) -> OrgMemory:
    return OrgMemory(
        memory_id=str(row["memory_id"]),
        org_id=str(row["org_id"]),
        created_by=str(row["created_by"]),
        content=row["content"],
        category=row["category"],
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
    )
