"""Supabase CRUD for Scope-3 SBTi/FLAG targets (Epic D). Imports ONLY db.client;
org_id resolved by the route. Written but NOT yet run against a live DB."""

from __future__ import annotations

from db.client import get_user_client


def create_target(*, access_token: str, org_id: str, user_id: str, fields: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: v for k, v in fields.items() if v is not None})
    return client.table("s3_targets").insert(row).execute().data[0]


def get_target(*, access_token: str, target_id: int) -> dict | None:
    client = get_user_client(access_token)
    resp = client.table("s3_targets").select("*").eq("target_id", target_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def list_targets(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_targets")
        .select("*")
        .eq("org_id", org_id)
        .order("target_id", desc=True)
        .execute()
    )
    return resp.data or []


def replace_target_categories(
    *, access_token: str, org_id: str, target_id: int, rows: list[dict]
) -> int:
    client = get_user_client(access_token)
    client.table("s3_target_categories").delete().eq("target_id", target_id).execute()
    if not rows:
        return 0
    payload = [{"org_id": org_id, "target_id": target_id, **r} for r in rows]
    resp = client.table("s3_target_categories").insert(payload).execute()
    return len(resp.data or [])


def list_target_categories(*, access_token: str, target_id: int) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_target_categories")
        .select("*")
        .eq("target_id", target_id)
        .order("category_num")
        .execute()
    )
    return resp.data or []


def upsert_flag_target(*, access_token: str, org_id: str, target_id: int, fields: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "target_id": target_id}
    row.update({k: v for k, v in fields.items() if v is not None})
    return client.table("s3_flag_targets").upsert(row, on_conflict="target_id").execute().data[0]


def get_flag_target(*, access_token: str, target_id: int) -> dict | None:
    client = get_user_client(access_token)
    resp = client.table("s3_flag_targets").select("*").eq("target_id", target_id).limit(1).execute()
    return resp.data[0] if resp.data else None
