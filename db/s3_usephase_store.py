"""Supabase CRUD for Scope-3 use-phase specs (Epic H). Imports ONLY db.client;
org_id resolved by the route. Written but NOT yet run against a live DB."""

from __future__ import annotations

from db.client import get_user_client

_FIELDS = (
    "product_ref",
    "energy_per_use_kwh",
    "water_l_per_use",
    "standby_power_w",
    "fuel_kwh_per_use",
    "spec_source",
    "uses_per_year",
    "lifetime_years",
    "sub_sector",
    "units_sold",
    "region",
    "mode",
)


def create_spec(*, access_token: str, org_id: str, user_id: str, spec: dict) -> dict:
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: spec[k] for k in _FIELDS if k in spec and spec[k] is not None})
    return client.table("s3_use_phase_specs").insert(row).execute().data[0]


def list_specs(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_use_phase_specs")
        .select("*")
        .eq("org_id", org_id)
        .order("spec_id", desc=True)
        .execute()
    )
    return resp.data or []


def delete_spec(*, access_token: str, spec_id: int) -> None:
    client = get_user_client(access_token)
    client.table("s3_use_phase_specs").delete().eq("spec_id", spec_id).execute()
