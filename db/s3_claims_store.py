"""Supabase CRUD for Scope-3 green-claim assessments (Epic I). Imports ONLY
db.client; org_id resolved by the route. Written but NOT yet run against a live DB."""

from __future__ import annotations

from db.client import get_user_client


def save_claim(*, access_token: str, org_id: str, user_id: str, fields: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: v for k, v in fields.items() if v is not None})
    return client.table("s3_claims").insert(row).execute().data[0]


def list_claims(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_claims")
        .select("*")
        .eq("org_id", org_id)
        .order("claim_id", desc=True)
        .execute()
    )
    return resp.data or []
