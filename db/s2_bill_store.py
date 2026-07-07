"""Read + write access to Scope 2 utility accounts and bills (migration 041).

Reads return non-superseded bills flattened with their site + energy carrier (via
the account embed), ready to map to engine ConsumptionRecords. Writes persist CSV
imports: find-or-create an account per (site, carrier) and insert bill rows.
Isolated Scope 2 store — imports only db.client.
"""

from __future__ import annotations

from db.client import get_user_client


def get_or_create_account(
    site_id: int,
    energy_carrier: str,
    *,
    org_id: str,
    user_id: str,
    access_token: str,
) -> int:
    """Return the csv-source account for (site, carrier), creating it if absent."""
    client = get_user_client(access_token)
    existing = (
        client.table("s2_utility_accounts")
        .select("account_id")
        .eq("site_id", site_id)
        .eq("energy_carrier", energy_carrier)
        .eq("source_type", "csv")
        .limit(1)
        .execute()
    )
    if existing.data:
        return int(existing.data[0]["account_id"])
    response = (
        client.table("s2_utility_accounts")
        .insert(
            {
                "site_id": site_id,
                "org_id": org_id,
                "user_id": user_id,
                "energy_carrier": energy_carrier,
                "source_type": "csv",
            }
        )
        .execute()
    )
    return int(response.data[0]["account_id"])


def insert_bills(
    rows: list[dict], *, org_id: str, user_id: str, access_token: str
) -> list[dict]:
    """Insert bill rows (already carrying account_id); return the inserted rows.

    Returned rows include the DB-assigned bill_id plus the fields dedup needs, so
    callers can reconcile them against existing active bills. Use len() for a count.
    """
    if not rows:
        return []
    client = get_user_client(access_token)
    payload = [{**row, "org_id": org_id, "user_id": user_id} for row in rows]
    response = client.table("s2_utility_bills").insert(payload).execute()
    return response.data or []


def list_active_bill_keys(account_ids: list[int], access_token: str) -> list[dict]:
    """Active (non-superseded) bills for the given accounts, keyed for dedup.

    Returns bill_id, account_id, period bounds, and the estimated/cost-only flags —
    the shape s2_ingestion.dedup.BillKey consumes. Empty account list -> no query.
    """
    if not account_ids:
        return []
    client = get_user_client(access_token)
    response = (
        client.table("s2_utility_bills")
        .select(
            "bill_id, account_id, period_start, period_end, "
            "is_estimated_read, is_cost_only"
        )
        .in_("account_id", account_ids)
        .is_("superseded_by_bill_id", "null")
        .execute()
    )
    return response.data or []


def supersede_bills(pairs: list[tuple[int, int]], *, access_token: str) -> int:
    """Mark each superseded bill with its superseding bill_id (PRD 5.6).

    `pairs` is (superseded_bill_id, superseding_bill_id). Consumption is never
    rewritten — only the superseded_by_bill_id pointer is set, which drops the row
    from list_active_bills / the calc engine. Returns the number of rows updated.
    """
    if not pairs:
        return 0
    client = get_user_client(access_token)
    updated = 0
    for superseded_id, superseding_id in pairs:
        response = (
            client.table("s2_utility_bills")
            .update({"superseded_by_bill_id": superseding_id})
            .eq("bill_id", superseded_id)
            .execute()
        )
        updated += len(response.data or [])
    return updated


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
