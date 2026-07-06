"""Supabase CRUD for the Scope-3 obligation front door (Epic C).

Imports ONLY db.client (tenancy rule); org_id is resolved by the route layer.
User-scoped client so RLS (public.is_org_member(org_id)) is enforced.

Written but NOT yet run against a live DB ("write code now, apply later").
"""

from __future__ import annotations

from db.client import get_user_client

_PROFILE_FIELDS = (
    "annual_revenue_usd",
    "employee_count",
    "is_us_entity",
    "does_business_in_ca",
    "eu_turnover_eur",
    "eu_subsidiary",
    "eu_branch_turnover_eur",
    "listed_jurisdictions",
    "sector",
    "is_flag_sector",
    "key_customers",
)


def upsert_company_profile(*, access_token: str, org_id: str, user_id: str, profile: dict) -> dict:
    """Insert or update the org's single company profile (UNIQUE org_id)."""
    client = get_user_client(access_token)
    row = {"org_id": org_id, "user_id": user_id}
    row.update({k: profile[k] for k in _PROFILE_FIELDS if k in profile})
    resp = client.table("s3_company_profiles").upsert(row, on_conflict="org_id").execute()
    return resp.data[0]


def get_company_profile(*, access_token: str, org_id: str) -> dict | None:
    client = get_user_client(access_token)
    resp = client.table("s3_company_profiles").select("*").eq("org_id", org_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def save_obligations(
    *, access_token: str, org_id: str, user_id: str, obligations: list[dict]
) -> int:
    """Replace the org's evaluated obligations with a fresh engine run."""
    client = get_user_client(access_token)
    client.table("s3_obligations").delete().eq("org_id", org_id).execute()
    if not obligations:
        return 0
    rows = [{"org_id": org_id, "user_id": user_id, **o} for o in obligations]
    resp = client.table("s3_obligations").insert(rows).execute()
    return len(resp.data or [])


def list_obligations(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_obligations")
        .select("*")
        .eq("org_id", org_id)
        .order("priority", desc=True)
        .execute()
    )
    return resp.data or []
