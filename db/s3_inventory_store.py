"""Supabase CRUD for the Scope-3 corporate inventory (Epic A).

Per the tenancy rule this store imports ONLY db.client: `org_id` is resolved in
the route layer (via db.org_store) and passed in. All access goes through the
user-scoped client so RLS (public.is_org_member(org_id)) is enforced by Postgres.

NOTE: written but NOT yet exercised against a live database ("write code now,
apply later"). Verify once migrations 300-303 are applied to an isolated DB.
"""

from __future__ import annotations

from db.client import get_user_client

_VERSION_COLS = (
    "inventory_id, org_id, reporting_year, boundary_approach, status, "
    "is_base_year, total_kg_co2e, version, created_at, locked_at"
)


# --- inventory versions -----------------------------------------------------


def create_inventory_version(
    *, access_token: str, org_id: str, user_id: str, reporting_year: int, boundary_approach: str
) -> dict:
    client = get_user_client(access_token)
    row = {
        "org_id": org_id,
        "user_id": user_id,
        "reporting_year": reporting_year,
        "boundary_approach": boundary_approach,
        "status": "draft",
    }
    resp = client.table("s3_inventory_versions").insert(row).execute()
    return resp.data[0]


def get_inventory_version(*, access_token: str, inventory_id: int) -> dict | None:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_inventory_versions")
        .select(_VERSION_COLS)
        .eq("inventory_id", inventory_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def list_inventory_versions(*, access_token: str, org_id: str) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_inventory_versions")
        .select(_VERSION_COLS)
        .eq("org_id", org_id)
        .order("reporting_year", desc=True)
        .execute()
    )
    return resp.data or []


def set_inventory_total(*, access_token: str, inventory_id: int, total_kg_co2e: float) -> None:
    client = get_user_client(access_token)
    (
        client.table("s3_inventory_versions")
        .update({"total_kg_co2e": total_kg_co2e, "status": "calculated"})
        .eq("inventory_id", inventory_id)
        .execute()
    )


def lock_inventory_version(*, access_token: str, inventory_id: int) -> dict | None:
    from datetime import UTC, datetime

    client = get_user_client(access_token)
    resp = (
        client.table("s3_inventory_versions")
        .update({"status": "locked", "locked_at": datetime.now(UTC).isoformat()})
        .eq("inventory_id", inventory_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


# --- spend records ----------------------------------------------------------


def insert_spend_records(
    *, access_token: str, org_id: str, inventory_id: int, user_id: str, records: list[dict]
) -> int:
    """Bulk-insert normalized spend lines. Each `record` is a plain dict of the
    canonical fields; org_id / inventory_id / user_id are stamped here."""
    if not records:
        return 0
    client = get_user_client(access_token)
    rows = [
        {
            "org_id": org_id,
            "inventory_id": inventory_id,
            "user_id": user_id,
            **{k: v for k, v in rec.items() if v is not None},
        }
        for rec in records
    ]
    resp = client.table("s3_spend_records").insert(rows).execute()
    return len(resp.data or [])


def list_spend_records(*, access_token: str, inventory_id: int) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_spend_records")
        .select("*")
        .eq("inventory_id", inventory_id)
        .order("spend_record_id")
        .execute()
    )
    return resp.data or []


# --- classifications --------------------------------------------------------


def insert_classifications(*, access_token: str, org_id: str, classifications: list[dict]) -> int:
    if not classifications:
        return 0
    client = get_user_client(access_token)
    rows = [{"org_id": org_id, **c} for c in classifications]
    resp = client.table("s3_spend_classifications").insert(rows).execute()
    return len(resp.data or [])


# --- category results -------------------------------------------------------


def upsert_category_results(
    *, access_token: str, org_id: str, inventory_id: int, results: list[dict]
) -> None:
    """Replace the category results for an inventory version (idempotent recompute)."""
    client = get_user_client(access_token)
    client.table("s3_inventory_category_results").delete().eq(
        "inventory_id", inventory_id
    ).execute()
    if not results:
        return
    rows = [{"org_id": org_id, "inventory_id": inventory_id, **r} for r in results]
    client.table("s3_inventory_category_results").insert(rows).execute()


def list_category_results(*, access_token: str, inventory_id: int) -> list[dict]:
    client = get_user_client(access_token)
    resp = (
        client.table("s3_inventory_category_results")
        .select("*")
        .eq("inventory_id", inventory_id)
        .order("scope3_category")
        .execute()
    )
    return resp.data or []
