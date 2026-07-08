"""Scope 2 target-setting store — SBTi-style reduction trajectories (migration 049).

Org-scoped RLS via is_org_member. All queries filter by user context.
"""

from __future__ import annotations

from typing import Any

from db.client import get_user_client


def list_targets(org_id: str, access_token: str) -> list[dict[str, Any]]:
    """Get all targets for the org."""
    client = get_user_client(access_token)
    return (
        client.table("s2_targets")
        .select("*")
        .eq("org_id", org_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def get_active_target(org_id: str, access_token: str) -> dict[str, Any] | None:
    """Get the currently active target (status='active') for the org."""
    client = get_user_client(access_token)
    results = (
        client.table("s2_targets")
        .select("*")
        .eq("org_id", org_id)
        .eq("status", "active")
        .execute()
        .data
    )
    return results[0] if results else None


def create_target(
    payload: dict[str, Any],
    *,
    org_id: str,
    user_id: str,
    access_token: str,
) -> int:
    """Create a new target. Returns target_id."""
    client = get_user_client(access_token)
    data = {
        **payload,
        "org_id": org_id,
        "status": "draft",
    }
    result = client.table("s2_targets").insert(data).execute()
    return result.data[0]["target_id"]


def get_target(target_id: int, access_token: str) -> dict[str, Any] | None:
    """Fetch a single target by ID (RLS enforces org membership)."""
    client = get_user_client(access_token)
    results = client.table("s2_targets").select("*").eq("target_id", target_id).execute().data
    return results[0] if results else None


def update_target(
    target_id: int,
    updates: dict[str, Any],
    *,
    access_token: str,
) -> None:
    """Update target metadata (status, notes); immutable fields are omitted."""
    client = get_user_client(access_token)
    client.table("s2_targets").update(updates).eq("target_id", target_id).execute()


def delete_target(target_id: int, *, access_token: str) -> None:
    """Delete a target."""
    client = get_user_client(access_token)
    client.table("s2_targets").delete().eq("target_id", target_id).execute()
