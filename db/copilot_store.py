"""Supabase schema and CRUD for the Supplier Engagement Copilot.

Tables (managed by supabase/migrations/):
  suppliers   — shared contact directory (seeded in migration)
  engagements — user-owned engagement lifecycle records
  audit_log   — user-owned append-only event log

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from db.client import get_user_client


@dataclass
class Supplier:
    supplier_id: int
    supplier_name: str
    contact_name: str | None
    contact_email: str | None


@dataclass
class Engagement:
    engagement_id: int
    supplier_name: str
    product_name: str
    component_name: str | None
    material: str | None
    kg_co2e: float | None
    share_pct: float | None
    status: str
    email_draft: str | None
    email_sent: str | None
    response_received: str | None
    routing_decision: str | None
    decision_rationale: str | None
    ghg_protocol_citation: str | None
    next_step: str | None
    created_at: str
    last_action_date: str | None


@dataclass
class AuditEntry:
    log_id: int
    timestamp: str
    event: str
    workflow: str
    model: str | None
    supplier_name: str | None
    product_name: str | None
    component_name: str | None
    email_sent: str | None
    response_received: str | None
    routing_decision: str | None
    decision_rationale: str | None
    ghg_protocol_citation: str | None
    data_collected: str | None
    status: str | None


def init_copilot_db() -> None:
    """No-op: schema and supplier seed data are managed by supabase/migrations/."""


def get_all_suppliers(access_token: str) -> list[Supplier]:
    client = get_user_client(access_token)
    response = client.table("suppliers").select("*").order("supplier_name").execute()
    return [_supplier_from_row(row) for row in response.data]


def get_supplier_by_name(name: str, access_token: str) -> Supplier | None:
    client = get_user_client(access_token)
    response = (
        client.table("suppliers")
        .select("*")
        .ilike("supplier_name", name)
        .limit(1)
        .execute()
    )
    if response.data:
        return _supplier_from_row(response.data[0])
    return None


def create_engagement(
    supplier_name: str,
    product_name: str,
    component_name: str | None,
    material: str | None,
    kg_co2e: float | None,
    share_pct: float | None,
    *,
    user_id: str,
    access_token: str,
    email_draft: str | None = None,
) -> int:
    """Insert a new engagement row and return its engagement_id."""
    client = get_user_client(access_token)
    now = _utc_now_iso()
    response = (
        client.table("engagements")
        .insert(
            {
                "user_id": user_id,
                "supplier_name": supplier_name,
                "product_name": product_name,
                "component_name": component_name,
                "material": material,
                "kg_co2e": kg_co2e,
                "share_pct": share_pct,
                "email_draft": email_draft,
                "status": "open",
                "created_at": now,
                "last_action_date": now,
            }
        )
        .execute()
    )
    return int(response.data[0]["engagement_id"])


def update_engagement(
    engagement_id: int,
    *,
    access_token: str,
    **fields,
) -> None:
    """Update any subset of engagement fields by keyword argument."""
    allowed = {
        "status",
        "email_draft",
        "email_sent",
        "response_received",
        "routing_decision",
        "decision_rationale",
        "ghg_protocol_citation",
        "next_step",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return
    updates["last_action_date"] = _utc_now_iso()
    client = get_user_client(access_token)
    client.table("engagements").update(updates).eq("engagement_id", engagement_id).execute()


def get_engagement(engagement_id: int, access_token: str) -> Engagement | None:
    client = get_user_client(access_token)
    response = (
        client.table("engagements")
        .select("*")
        .eq("engagement_id", engagement_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _engagement_from_row(response.data[0])


def get_engagements_for_product(product_name: str, access_token: str) -> list[Engagement]:
    client = get_user_client(access_token)
    response = (
        client.table("engagements")
        .select("*")
        .eq("product_name", product_name)
        .order("share_pct", desc=True)
        .execute()
    )
    return [_engagement_from_row(row) for row in response.data]


def get_all_engagements(access_token: str) -> list[Engagement]:
    client = get_user_client(access_token)
    response = (
        client.table("engagements").select("*").order("created_at", desc=True).execute()
    )
    return [_engagement_from_row(row) for row in response.data]


def append_audit_log(
    event: str,
    workflow: str,
    *,
    user_id: str,
    access_token: str,
    supplier_name: str | None = None,
    product_name: str | None = None,
    component_name: str | None = None,
    model: str | None = None,
    email_sent: str | None = None,
    response_received: str | None = None,
    routing_decision: str | None = None,
    decision_rationale: str | None = None,
    ghg_protocol_citation: str | None = None,
    data_collected: str | None = None,
    status: str | None = None,
) -> None:
    """Append one row to the audit log."""
    client = get_user_client(access_token)
    client.table("audit_log").insert(
        {
            "user_id": user_id,
            "event": event,
            "workflow": workflow,
            "model": model,
            "supplier_name": supplier_name,
            "product_name": product_name,
            "component_name": component_name,
            "email_sent": email_sent,
            "response_received": response_received,
            "routing_decision": routing_decision,
            "decision_rationale": decision_rationale,
            "ghg_protocol_citation": ghg_protocol_citation,
            "data_collected": data_collected,
            "status": status,
        }
    ).execute()


def get_audit_log(
    access_token: str,
    supplier_name: str | None = None,
    product_name: str | None = None,
) -> list[AuditEntry]:
    """Return audit log rows, optionally filtered by supplier or product."""
    client = get_user_client(access_token)
    query = client.table("audit_log").select("*")
    if supplier_name:
        query = query.eq("supplier_name", supplier_name)
    if product_name:
        query = query.eq("product_name", product_name)
    response = query.order("timestamp", desc=True).execute()
    return [_audit_from_row(row) for row in response.data]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _supplier_from_row(row: dict) -> Supplier:
    return Supplier(
        supplier_id=int(row["supplier_id"]),
        supplier_name=row["supplier_name"],
        contact_name=row.get("contact_name"),
        contact_email=row.get("contact_email"),
    )


def _engagement_from_row(row: dict) -> Engagement:
    return Engagement(
        engagement_id=int(row["engagement_id"]),
        supplier_name=row["supplier_name"],
        product_name=row["product_name"],
        component_name=row.get("component_name"),
        material=row.get("material"),
        kg_co2e=row.get("kg_co2e"),
        share_pct=row.get("share_pct"),
        status=row["status"],
        email_draft=row.get("email_draft"),
        email_sent=row.get("email_sent"),
        response_received=row.get("response_received"),
        routing_decision=row.get("routing_decision"),
        decision_rationale=row.get("decision_rationale"),
        ghg_protocol_citation=row.get("ghg_protocol_citation"),
        next_step=row.get("next_step"),
        created_at=str(row.get("created_at", "")),
        last_action_date=str(row["last_action_date"]) if row.get("last_action_date") else None,
    )


def _audit_from_row(row: dict) -> AuditEntry:
    return AuditEntry(
        log_id=int(row["log_id"]),
        timestamp=str(row.get("timestamp", "")),
        event=row["event"],
        workflow=row["workflow"],
        model=row.get("model"),
        supplier_name=row.get("supplier_name"),
        product_name=row.get("product_name"),
        component_name=row.get("component_name"),
        email_sent=row.get("email_sent"),
        response_received=row.get("response_received"),
        routing_decision=row.get("routing_decision"),
        decision_rationale=row.get("decision_rationale"),
        ghg_protocol_citation=row.get("ghg_protocol_citation"),
        data_collected=row.get("data_collected"),
        status=row.get("status"),
    )
