"""Supabase CRUD for Scope 2 landlord data-requests (migration 043).

Isolated Scope 2 store — imports only db.client. Reads embed the site name so the
request queue can show which site each request belongs to.
"""

from __future__ import annotations

from db.client import get_user_client

_COLUMNS = (
    "request_id, site_id, org_id, user_id, landlord_contact, method, status, "
    "sent_at, responded_at, reminder_cadence_days, returned_data_ref, notes, "
    "created_at, updated_at"
)


def create_request(payload: dict, *, org_id: str, user_id: str, access_token: str) -> int:
    client = get_user_client(access_token)
    row = {**payload, "org_id": org_id, "user_id": user_id}
    response = client.table("s2_landlord_requests").insert(row).execute()
    return int(response.data[0]["request_id"])


def list_requests(access_token: str) -> list[dict]:
    """All landlord requests visible to the caller, with the site name attached."""
    client = get_user_client(access_token)
    response = (
        client.table("s2_landlord_requests")
        .select(f"{_COLUMNS}, s2_sites(name)")
        .order("created_at", desc=True)
        .execute()
    )
    out: list[dict] = []
    for row in response.data:
        site = row.pop("s2_sites", None) or {}
        row["site_name"] = site.get("name")
        out.append(row)
    return out


def get_request(request_id: int, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    response = (
        client.table("s2_landlord_requests")
        .select(_COLUMNS)
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def update_request(request_id: int, updates: dict, *, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    client.table("s2_landlord_requests").update(updates).eq(
        "request_id", request_id
    ).execute()
    return get_request(request_id, access_token)


def delete_request(request_id: int, *, access_token: str) -> None:
    client = get_user_client(access_token)
    existing = (
        client.table("s2_landlord_requests")
        .select("request_id")
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Landlord request {request_id} not found.")
    client.table("s2_landlord_requests").delete().eq("request_id", request_id).execute()
