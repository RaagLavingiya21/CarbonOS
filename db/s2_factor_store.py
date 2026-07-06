"""Read access to the Scope 2 grid emission-factor library (migration 042).

Global reference data (read-only to users; seeded via service role). Isolated
Scope 2 store — imports only db.client.
"""

from __future__ import annotations

from db.client import get_user_client

_COLUMNS = "factor_type, region_code, vintage_year, kg_co2e_per_mwh, source_citation"


def load_factors(access_token: str) -> list[dict]:
    """Return all factor rows (the caller builds a FactorLibrary from them)."""
    client = get_user_client(access_token)
    return client.table("s2_factor_library").select(_COLUMNS).execute().data
