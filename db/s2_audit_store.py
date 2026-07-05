"""Append-only Scope 2 audit-log writes (migration 046).

Every calculation persists its per-site audit payload here so any reported tCO2e
traces to source + factor + formula. The migration has no UPDATE/DELETE policy, so
the log is immutable. Isolated Scope 2 store — imports only db.client.
"""

from __future__ import annotations

from db.client import get_user_client


def insert_calc_audit_entries(
    audit_entries: list[dict],
    *,
    calc_id: int,
    org_id: str,
    user_id: str,
    access_token: str,
) -> None:
    """Persist the engine's per-site audit entries for a calculation."""
    if not audit_entries:
        return
    client = get_user_client(access_token)
    rows = []
    for entry in audit_entries:
        location = entry.get("location_based", {})
        rows.append(
            {
                "org_id": org_id,
                "user_id": user_id,
                "calc_id": calc_id,
                "entity_type": "calculation",
                "entity_id": None,
                "factor_source": location.get("source_citation"),
                "factor_version": location.get("factor_vintage"),
                "formula": location.get("formula"),
                "intermediate_values": entry,
            }
        )
    client.table("s2_audit_log").insert(rows).execute()
