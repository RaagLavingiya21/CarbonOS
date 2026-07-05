"""Persistence for Scope 2 dual-method calculation results (migration 045).

Versioned/immutable: each run INSERTs a new calc_id; rows are never updated (the
migration has no UPDATE policy). Isolated Scope 2 store — imports only db.client.
"""

from __future__ import annotations

from db.client import get_user_client

_COLUMNS = (
    "calc_id, org_id, reporting_year, scope, site_id, location_based_kg_co2e, "
    "market_based_kg_co2e, consumption_mwh, market_tier, market_fallback_flagged, "
    "factor_versions, methodology_notes, created_at"
)


def save_calculation(
    row: dict, *, org_id: str, user_id: str, access_token: str
) -> int:
    """Insert a calculation snapshot; returns the new calc_id."""
    client = get_user_client(access_token)
    payload = {**row, "org_id": org_id, "user_id": user_id, "created_by": user_id}
    response = client.table("s2_calculations").insert(payload).execute()
    return int(response.data[0]["calc_id"])


def list_calculations(access_token: str) -> list[dict]:
    client = get_user_client(access_token)
    return (
        client.table("s2_calculations")
        .select(_COLUMNS)
        .order("created_at", desc=True)
        .execute()
        .data
    )
