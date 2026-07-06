"""Supabase CRUD for Scope 2 sites (migration 040_s2_sites.sql).

Isolated Scope 2 store — imports only the shared db.client. Never touches any
Carbon OS (Scope 3 / PACT) table. org_id is resolved in the route layer and passed
in; RLS (org-scoped) enforces tenancy.
"""

from __future__ import annotations

from db.client import get_user_client

_COLUMNS = (
    "site_id, org_id, user_id, name, site_type, address, zip, country, "
    "egrid_subregion, iea_country, ownership, lease_type, franchise_flag, "
    "scope3_cat14_note, consolidation_approach, status, created_at, updated_at"
)


def create_site(payload: dict, *, org_id: str, user_id: str, access_token: str) -> int:
    client = get_user_client(access_token)
    row = {**payload, "org_id": org_id, "user_id": user_id}
    response = client.table("s2_sites").insert(row).execute()
    return int(response.data[0]["site_id"])


def list_sites(access_token: str) -> list[dict]:
    """All sites visible to the caller (RLS scopes to their org)."""
    client = get_user_client(access_token)
    return (
        client.table("s2_sites")
        .select(_COLUMNS)
        .order("created_at", desc=True)
        .execute()
        .data
    )


def get_site(site_id: int, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    response = (
        client.table("s2_sites")
        .select(_COLUMNS)
        .eq("site_id", site_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def update_site(site_id: int, updates: dict, *, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    client.table("s2_sites").update(updates).eq("site_id", site_id).execute()
    return get_site(site_id, access_token)


def delete_site(site_id: int, *, access_token: str) -> None:
    client = get_user_client(access_token)
    existing = (
        client.table("s2_sites").select("site_id").eq("site_id", site_id).limit(1).execute()
    )
    if not existing.data:
        raise ValueError(f"Site {site_id} not found.")
    client.table("s2_sites").delete().eq("site_id", site_id).execute()
