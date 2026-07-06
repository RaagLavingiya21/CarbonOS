"""Supabase CRUD for the inbound buyer/CDP request queue (migration 044).

Isolated Scope 2 store — imports only db.client.
"""

from __future__ import annotations

from db.client import get_user_client

_COLUMNS = (
    "request_id, org_id, user_id, buyer_name, destination, reporting_year, "
    "due_date, status, calc_id, answered_at, notes, created_at, updated_at"
)


def create_request(payload: dict, *, org_id: str, user_id: str, access_token: str) -> int:
    client = get_user_client(access_token)
    row = {**payload, "org_id": org_id, "user_id": user_id}
    response = client.table("s2_buyer_requests").insert(row).execute()
    return int(response.data[0]["request_id"])


def list_requests(access_token: str) -> list[dict]:
    client = get_user_client(access_token)
    return (
        client.table("s2_buyer_requests")
        .select(_COLUMNS)
        .order("due_date", desc=False, nullsfirst=False)
        .execute()
        .data
    )


def get_request(request_id: int, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    response = (
        client.table("s2_buyer_requests")
        .select(_COLUMNS)
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def update_request(request_id: int, updates: dict, *, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    client.table("s2_buyer_requests").update(updates).eq(
        "request_id", request_id
    ).execute()
    return get_request(request_id, access_token)


def delete_request(request_id: int, *, access_token: str) -> None:
    client = get_user_client(access_token)
    existing = (
        client.table("s2_buyer_requests")
        .select("request_id")
        .eq("request_id", request_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Buyer request {request_id} not found.")
    client.table("s2_buyer_requests").delete().eq("request_id", request_id).execute()
