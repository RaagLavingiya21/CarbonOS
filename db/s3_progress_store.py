"""Supabase CRUD for Scope-3 progress + base-year recalc (Epic E). Imports ONLY
db.client; org_id resolved by the route. Written but NOT yet run against a live DB."""

from __future__ import annotations

from db.client import get_user_client


def save_progress(*, access_token: str, org_id: str, user_id: str, fields: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: v for k, v in fields.items() if v is not None})
    return client.table("s3_target_progress").insert(row).execute().data[0]


def list_progress(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_target_progress")
        .select("*")
        .eq("org_id", org_id)
        .order("progress_id", desc=True)
        .execute()
    )
    return resp.data or []


def save_recalc(*, access_token: str, org_id: str, user_id: str, fields: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: v for k, v in fields.items() if v is not None})
    return client.table("s3_base_year_recalcs").insert(row).execute().data[0]


def list_recalcs(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_base_year_recalcs")
        .select("*")
        .eq("org_id", org_id)
        .order("recalc_id", desc=True)
        .execute()
    )
    return resp.data or []
