"""Read + write access to the Scope 2 EAC / contractual-instrument registry (047).

RECs / GOs / green tariffs / PPAs that back market-based accounting. Reads for a
reporting year feed s2_calc.mappers.eac_from_row -> the engine's quality screen.
Isolated Scope 2 store — imports only db.client.
"""

from __future__ import annotations

from db.client import get_user_client

_COLUMNS = (
    "instrument_id, site_id, org_id, instrument_type, reporting_year, mwh, "
    "region_market, vintage_year, kg_co2e_per_mwh, specific_generation_attribute, "
    "unique_no_double_count, registry_tracked, retired_for_buyer, not_an_offset, "
    "transparent, registry_name, retirement_id, retirement_date, notes, created_at"
)


def list_eacs(access_token: str) -> list[dict]:
    """All EAC instruments visible to the caller (org-scoped by RLS)."""
    client = get_user_client(access_token)
    response = (
        client.table("s2_eac_instruments")
        .select(_COLUMNS)
        .order("reporting_year", desc=True)
        .order("instrument_id", desc=True)
        .execute()
    )
    return response.data or []


def list_eacs_for_year(reporting_year: int, access_token: str) -> list[dict]:
    """EAC instruments for one reporting year — the calc-engine input set."""
    client = get_user_client(access_token)
    response = (
        client.table("s2_eac_instruments")
        .select(_COLUMNS)
        .eq("reporting_year", reporting_year)
        .execute()
    )
    return response.data or []


def create_eac(payload: dict, *, org_id: str, user_id: str, access_token: str) -> int:
    """Insert one EAC instrument; returns its id."""
    client = get_user_client(access_token)
    response = (
        client.table("s2_eac_instruments")
        .insert({**payload, "org_id": org_id, "user_id": user_id})
        .execute()
    )
    return int(response.data[0]["instrument_id"])


def get_eac(instrument_id: int, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    response = (
        client.table("s2_eac_instruments")
        .select(_COLUMNS)
        .eq("instrument_id", instrument_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def delete_eac(instrument_id: int, *, access_token: str) -> None:
    client = get_user_client(access_token)
    client.table("s2_eac_instruments").delete().eq(
        "instrument_id", instrument_id
    ).execute()
