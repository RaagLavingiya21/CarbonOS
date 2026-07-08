"""Supabase CRUD for Scope-3 suppliers (Epic F). Imports ONLY db.client; org_id
resolved by the route. Written but NOT yet run against a live DB."""

from __future__ import annotations

from db.client import get_user_client

_FIELDS = (
    "name",
    "scope3_category",
    "emissions_kg",
    "spend_usd",
    "pcf_received",
    "dq_score",
    "supplier_sbt_status",
)


def create_supplier(*, access_token: str, org_id: str, user_id: str, supplier: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: supplier[k] for k in _FIELDS if k in supplier})
    return client.table("s3_suppliers").insert(row).execute().data[0]


def list_suppliers(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_suppliers")
        .select("*")
        .eq("org_id", org_id)
        .order("emissions_kg", desc=True)
        .execute()
    )
    return resp.data or []


def delete_supplier(*, access_token: str, supplier_id: int) -> None:
    client = get_user_client(access_token)
    client.table("s3_suppliers").delete().eq("supplier_id", supplier_id).execute()
