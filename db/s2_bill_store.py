"""Read access to active Scope 2 utility bills (migration 041).

Returns non-superseded bills flattened with their site + energy carrier (via the
account embed), ready to map to engine ConsumptionRecords. Isolated Scope 2 store —
imports only db.client.
"""

from __future__ import annotations

from db.client import get_user_client


def list_active_bills(access_token: str) -> list[dict]:
    """Active (non-superseded) bills with site_id + energy_carrier attached."""
    client = get_user_client(access_token)
    response = (
        client.table("s2_utility_bills")
        .select(
            "bill_id, canonical_mwh, period_start, period_end, is_estimated_read, "
            "is_cost_only, s2_utility_accounts!inner(site_id, energy_carrier)"
        )
        .is_("superseded_by_bill_id", "null")
        .execute()
    )
    flattened: list[dict] = []
    for row in response.data:
        account = row.get("s2_utility_accounts") or {}
        flattened.append(
            {
                "bill_id": row["bill_id"],
                "canonical_mwh": row.get("canonical_mwh"),
                "period_start": row["period_start"],
                "period_end": row["period_end"],
                "is_estimated_read": row.get("is_estimated_read", False),
                "is_cost_only": row.get("is_cost_only", False),
                "site_id": account.get("site_id"),
                "energy_carrier": account.get("energy_carrier"),
            }
        )
    return flattened
