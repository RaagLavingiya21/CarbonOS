"""Supabase CRUD for platform chat agent active module panels.

Tables (managed by supabase/migrations/):
  active_panels — persisted module panel state per user

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from db.client import get_user_client

_PANEL_COLUMNS = (
    "panel_id, user_id, thread_id, module_type, panel_state, "
    "tab_order, is_active, created_at, updated_at"
)


@dataclass
class ActivePanel:
    panel_id: str
    user_id: str
    thread_id: str | None
    module_type: str
    panel_state: dict[str, Any]
    tab_order: int
    is_active: bool
    created_at: str
    updated_at: str


def create_panel(
    module_type: str,
    *,
    user_id: str,
    access_token: str,
    thread_id: str | None = None,
    panel_state: dict[str, Any] | None = None,
    tab_order: int = 0,
    is_active: bool = True,
) -> str:
    """Insert an active panel and return its panel_id."""
    client = get_user_client(access_token)
    now = _utc_now_iso()
    payload: dict[str, Any] = {
        "user_id": user_id,
        "module_type": module_type.strip(),
        "panel_state": panel_state or {},
        "tab_order": tab_order,
        "is_active": is_active,
        "created_at": now,
        "updated_at": now,
    }
    if thread_id is not None:
        payload["thread_id"] = thread_id

    response = client.table("active_panels").insert(payload).execute()
    return str(response.data[0]["panel_id"])


def list_panels(access_token: str) -> list[ActivePanel]:
    """Return all active panels for the authenticated user."""
    client = get_user_client(access_token)
    response = (
        client.table("active_panels")
        .select(_PANEL_COLUMNS)
        .order("tab_order", desc=False)
        .execute()
    )
    return [_panel_from_row(row) for row in response.data]


def get_panel(panel_id: str, access_token: str) -> ActivePanel | None:
    """Return a single panel by ID, or None if not found / not owned."""
    client = get_user_client(access_token)
    response = (
        client.table("active_panels")
        .select(_PANEL_COLUMNS)
        .eq("panel_id", panel_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _panel_from_row(response.data[0])


def update_panel(panel_id: str, *, access_token: str, **fields) -> None:
    """Update panel_state, tab_order, is_active, and/or thread_id."""
    allowed = {"panel_state", "tab_order", "is_active", "thread_id"}
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    updates["updated_at"] = _utc_now_iso()
    client = get_user_client(access_token)
    client.table("active_panels").update(updates).eq("panel_id", panel_id).execute()


def delete_panel(panel_id: str, *, access_token: str) -> None:
    """Hard-delete an active panel."""
    client = get_user_client(access_token)
    client.table("active_panels").delete().eq("panel_id", panel_id).execute()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _panel_from_row(row: dict) -> ActivePanel:
    thread_id = row.get("thread_id")
    raw_state = row.get("panel_state")
    panel_state = raw_state if isinstance(raw_state, dict) else {}
    return ActivePanel(
        panel_id=str(row["panel_id"]),
        user_id=str(row["user_id"]),
        thread_id=str(thread_id) if thread_id is not None else None,
        module_type=row["module_type"],
        panel_state=panel_state,
        tab_order=int(row.get("tab_order", 0)),
        is_active=bool(row.get("is_active", True)),
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
    )
