"""Scope 1 Bayou credentials + sync state (data layer).

Credential-connect pattern: org-admin stores their Bayou API key via this layer;
the backend uses it to auto-fetch + parse bills. Keys are encrypted at-rest by
Supabase (via DATABASE_URL encryption) and never exposed to the frontend.

Sync scheduling is tracked (last_sync, next_sync) to enable background polling.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypedDict

from supabase import Client


class BayouCredentialRow(TypedDict, total=False):
    """Bayou credentials row (from s1_bayou_credentials table)."""
    id: str
    org_id: str
    bayou_api_key: str                 # never exposed to frontend
    is_active: bool
    last_sync: str | None              # ISO 8601 timestamp
    next_sync: str | None              # ISO 8601 timestamp
    sync_interval: str                 # PostgreSQL interval (e.g. '1 hour')
    created_by: str | None
    created_at: str
    updated_at: str


class NoCredentialsError(RuntimeError):
    """No Bayou credentials configured for this org."""


def get_or_create_credentials(
    org_id: str,
    client: Client,
    *,
    access_token: str,
) -> BayouCredentialRow:
    """Fetch org's Bayou credentials, or create an empty row (needs API key)."""
    try:
        resp = (
            client.table("s1_bayou_credentials")
            .select("*")
            .eq("org_id", org_id)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]
    except Exception:
        pass
    # Create an empty (inactive) row so org-admin can fill in the key
    resp = (
        client.table("s1_bayou_credentials")
        .insert({"org_id": org_id, "is_active": False, "bayou_api_key": ""})
        .execute()
    )
    return resp.data[0]


def set_api_key(
    org_id: str,
    api_key: str,
    client: Client,
    *,
    access_token: str,
) -> BayouCredentialRow:
    """Store org's Bayou API key (encrypted at-rest). Sets is_active=True."""
    resp = (
        client.table("s1_bayou_credentials")
        .update({
            "bayou_api_key": api_key,
            "is_active": True,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("org_id", org_id)
        .execute()
    )
    if not resp.data:
        raise NoCredentialsError(f"No Bayou credentials row for org {org_id}")
    return resp.data[0]


def get_active_api_key(
    org_id: str,
    client: Client,
    *,
    access_token: str,
) -> str:
    """Fetch org's active Bayou API key (for backend use only)."""
    resp = (
        client.table("s1_bayou_credentials")
        .select("bayou_api_key")
        .eq("org_id", org_id)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not resp.data or not resp.data[0].get("bayou_api_key"):
        raise NoCredentialsError(f"No active Bayou credentials for org {org_id}")
    return resp.data[0]["bayou_api_key"]


def mark_sync_complete(
    org_id: str,
    client: Client,
    *,
    access_token: str,
) -> BayouCredentialRow:
    """Update last_sync timestamp and schedule next_sync."""
    now = datetime.now(timezone.utc)
    next_sync_time = now + timedelta(hours=1)  # default 1-hour interval
    resp = (
        client.table("s1_bayou_credentials")
        .update({
            "last_sync": now.isoformat(),
            "next_sync": next_sync_time.isoformat(),
            "updated_at": now.isoformat(),
        })
        .eq("org_id", org_id)
        .execute()
    )
    if not resp.data:
        raise NoCredentialsError(f"No Bayou credentials row for org {org_id}")
    return resp.data[0]


def should_sync(
    org_id: str,
    client: Client,
    *,
    access_token: str,
) -> bool:
    """Check if org is due for a sync (next_sync <= now)."""
    resp = (
        client.table("s1_bayou_credentials")
        .select("next_sync, is_active")
        .eq("org_id", org_id)
        .limit(1)
        .execute()
    )
    if not resp.data or not resp.data[0].get("is_active"):
        return False
    next_sync_str = resp.data[0].get("next_sync")
    if not next_sync_str:
        return True  # never synced; sync now
    next_sync = datetime.fromisoformat(next_sync_str)
    return datetime.now(timezone.utc) >= next_sync
