"""Supabase CRUD for the Scope 1 module (isolated from Carbon OS stores).

Every write is org-scoped: the active org (db.org_store.get_active_org) supplies
org_id, and RLS (is_org_member) enforces isolation. No UI imports. Reads return
plain dicts (mirroring db.reader). See supabase/migrations/030-036.
"""

from __future__ import annotations

import hashlib
from uuid import uuid4

from db.client import get_service_client, get_user_client
from db.org_store import get_active_org

EVIDENCE_BUCKET = "s1-evidence"


class NoActiveOrgError(RuntimeError):
    """Raised when the caller has no active organization to scope Scope 1 data."""


def _org_and_client(access_token: str, user_id: str):
    org = get_active_org(access_token, user_id=user_id)
    if org is None:
        raise NoActiveOrgError("No active organization for the current user.")
    return org.id, get_user_client(access_token)


# --- Legal entities ---------------------------------------------------------

def create_entity(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_legal_entity").insert(row).execute().data[0]


def list_entities(*, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_legal_entity").select("*")
        .eq("org_id", org_id).order("created_at").execute().data
    )


def get_entity(entity_id: str, *, access_token: str, user_id: str) -> dict | None:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_legal_entity").select("*")
        .eq("org_id", org_id).eq("id", entity_id).limit(1).execute()
    )
    return resp.data[0] if resp.data else None


# --- Facilities -------------------------------------------------------------

def create_facility(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_facility").insert(row).execute().data[0]


def list_facilities(*, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_facility").select("*")
        .eq("org_id", org_id).order("created_at").execute().data
    )


# --- Data owners ------------------------------------------------------------

def create_data_owner(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_data_owner").insert(row).execute().data[0]


def list_data_owners(*, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_data_owner").select("*")
        .eq("org_id", org_id).order("created_at").execute().data
    )


def list_source_data_owners(*, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_source_data_owner").select("*")
        .eq("org_id", org_id).execute().data
    )


def assign_source_owner(
    emission_source_id: str, data_owner_id: str, *, access_token: str, user_id: str
) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {
        "org_id": org_id,
        "emission_source_id": emission_source_id,
        "data_owner_id": data_owner_id,
    }
    return (
        client.table("s1_source_data_owner")
        .upsert(row, on_conflict="emission_source_id,data_owner_id")
        .execute().data[0]
    )


# --- Inventories + boundary -------------------------------------------------

def create_inventory(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_inventory").insert(row).execute().data[0]


def get_inventory(inventory_id: str, *, access_token: str, user_id: str) -> dict | None:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_inventory").select("*")
        .eq("org_id", org_id).eq("id", inventory_id).limit(1).execute()
    )
    return resp.data[0] if resp.data else None


def list_inventories(*, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_inventory").select("*")
        .eq("org_id", org_id).order("reporting_year", desc=True).execute().data
    )


def set_base_year(inventory_id: str, patch: dict, *, access_token: str, user_id: str) -> dict:
    """Update an inventory's base-year fields (base_year / total / gwp_version)."""
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_inventory").update(patch)
        .eq("org_id", org_id).eq("id", inventory_id).execute()
    )
    return resp.data[0]


def set_inventory_metrics(inventory_id: str, patch: dict, *, access_token: str, user_id: str) -> dict:
    """Update an inventory's operational denominators (revenue/output/headcount)."""
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_inventory").update(patch)
        .eq("org_id", org_id).eq("id", inventory_id).execute()
    )
    return resp.data[0]


def lock_inventory(inventory_id: str, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_inventory")
        .update({"locked": True, "locked_by": user_id, "status": "final"})
        .eq("org_id", org_id).eq("id", inventory_id).execute()
    )
    return resp.data[0]


def upsert_boundary(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, **data}
    return (
        client.table("s1_inventory_entity_boundary")
        .upsert(row, on_conflict="inventory_id,entity_id")
        .execute().data[0]
    )


def list_boundaries(inventory_id: str, *, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_inventory_entity_boundary").select("*")
        .eq("org_id", org_id).eq("inventory_id", inventory_id).execute().data
    )


def log_boundary_decision(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "decided_by": user_id, **data}
    return client.table("s1_boundary_decision_log").insert(row).execute().data[0]


# --- Emission sources -------------------------------------------------------

def create_source(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_emission_source").insert(row).execute().data[0]


def list_sources(*, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_emission_source").select("*")
        .eq("org_id", org_id).order("created_at").execute().data
    )


def exclude_source(
    source_id: str, rationale: str, *, access_token: str, user_id: str
) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_emission_source")
        .update({"is_excluded": True, "exclusion_rationale": rationale})
        .eq("org_id", org_id).eq("id", source_id).execute()
    )
    return resp.data[0]


# --- Emission records -------------------------------------------------------

def create_record(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_emission_record").insert(row).execute().data[0]


def get_record(record_id: str, *, access_token: str, user_id: str) -> dict | None:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_emission_record").select("*")
        .eq("org_id", org_id).eq("id", record_id).limit(1).execute()
    )
    return resp.data[0] if resp.data else None


def list_records_for_inventory(
    inventory_id: str, *, access_token: str, user_id: str
) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_emission_record").select("*")
        .eq("org_id", org_id).eq("inventory_id", inventory_id).execute().data
    )


# --- Fugitive (refrigerant) records -----------------------------------------

def create_fugitive_record(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_fugitive_record").insert(row).execute().data[0]


def list_fugitive_records(inventory_id: str, *, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_fugitive_record").select("*")
        .eq("org_id", org_id).eq("inventory_id", inventory_id)
        .order("created_at").execute().data
    )


def delete_fugitive_record(record_id: str, *, access_token: str, user_id: str) -> dict | None:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_fugitive_record").delete()
        .eq("org_id", org_id).eq("id", record_id).execute()
    )
    return resp.data[0] if resp.data else None


# --- Base-year recalculation events -----------------------------------------

def list_recalc_events(inventory_id: str, *, access_token: str, user_id: str) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_base_year_recalc_event").select("*")
        .eq("org_id", org_id).eq("inventory_id", inventory_id)
        .order("created_at").execute().data
    )


def create_recalc_event(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_base_year_recalc_event").insert(row).execute().data[0]


def delete_recalc_event(event_id: str, *, access_token: str, user_id: str) -> dict | None:
    """Delete a not-yet-applied event (applied ones are immutable history)."""
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_base_year_recalc_event").delete()
        .eq("org_id", org_id).eq("id", event_id).eq("applied", False)
        .execute()
    )
    return resp.data[0] if resp.data else None


def mark_recalc_events_applied(
    event_ids: list[str], applied_at: str, *, access_token: str, user_id: str
) -> list[dict]:
    if not event_ids:
        return []
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_base_year_recalc_event")
        .update({"applied": True, "applied_at": applied_at})
        .eq("org_id", org_id).in_("id", event_ids).execute().data
    )


# --- Emission-factor overrides (per-org, admin-managed) ---------------------

def list_ef_overrides(
    *, access_token: str, user_id: str, active_only: bool = True
) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    q = client.table("s1_ef_override").select("*").eq("org_id", org_id)
    if active_only:
        q = q.is_("valid_to", "null")
    return q.order("created_at", desc=True).execute().data


def find_active_ef_override(match: dict, *, access_token: str, user_id: str) -> dict | None:
    """The org's current active override for a factor key, if any."""
    org_id, client = _org_and_client(access_token, user_id)
    q = (
        client.table("s1_ef_override").select("*")
        .eq("org_id", org_id).is_("valid_to", "null")
        .eq("fuel_or_activity", match["fuel_or_activity"])
        .eq("source_category", match["source_category"])
        .eq("gas", match["gas"])
        .eq("region", match.get("region", "US"))
    )
    my = match.get("model_year")
    q = q.is_("model_year", "null") if my is None else q.eq("model_year", my)
    resp = q.limit(1).execute()
    return resp.data[0] if resp.data else None


def create_ef_override(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_ef_override").insert(row).execute().data[0]


def retire_ef_override(
    override_id: str, valid_to: str, *, access_token: str, user_id: str
) -> dict | None:
    """Soft-retire an override (set valid_to); never hard-delete (history)."""
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_ef_override").update({"valid_to": valid_to})
        .eq("org_id", org_id).eq("id", override_id).is_("valid_to", "null")
        .execute()
    )
    return resp.data[0] if resp.data else None


# --- Collection status (readiness meter) ------------------------------------

def upsert_collection_status(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "updated_by": user_id, **data}
    return (
        client.table("s1_source_collection_status")
        .upsert(row, on_conflict="inventory_id,emission_source_id,period_start,period_end")
        .execute().data[0]
    )


def list_collection_status(
    inventory_id: str, *, access_token: str, user_id: str
) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_source_collection_status").select("*")
        .eq("org_id", org_id).eq("inventory_id", inventory_id).execute().data
    )


# --- Evidence ---------------------------------------------------------------

def evidence_row(
    file_bytes: bytes,
    *,
    file_name: str,
    content_type: str | None,
    document_type: str,
    org_id: str,
    inventory_id: str | None,
    user_id: str,
) -> dict:
    """Pure: build the evidence-document row with a server-computed SHA-256 and a
    tenant-scoped storage path. No I/O, so it is unit-testable."""
    digest = hashlib.sha256(file_bytes).hexdigest()
    storage_uri = f"{org_id}/{inventory_id or 'unassigned'}/{uuid4().hex}-{file_name}"
    return {
        "org_id": org_id,
        "inventory_id": inventory_id,
        "document_type": document_type,
        "file_name": file_name,
        "storage_uri": storage_uri,
        "content_type": content_type,
        "byte_size": len(file_bytes),
        "hash_sha256": digest,
        "uploaded_by": user_id,
    }


def _put_object(path: str, data: bytes, content_type: str | None) -> None:
    """Upload bytes to the private s1-evidence bucket (service role)."""
    get_service_client().storage.from_(EVIDENCE_BUCKET).upload(
        path, data, {"content-type": content_type or "application/octet-stream"}
    )


def upload_evidence(
    file_bytes: bytes,
    *,
    file_name: str,
    content_type: str | None,
    document_type: str,
    inventory_id: str | None,
    access_token: str,
    user_id: str,
) -> dict:
    """Store an evidence file: hash it, put the bytes in Storage, insert the row."""
    org_id, client = _org_and_client(access_token, user_id)
    row = evidence_row(
        file_bytes, file_name=file_name, content_type=content_type,
        document_type=document_type, org_id=org_id, inventory_id=inventory_id,
        user_id=user_id,
    )
    _put_object(row["storage_uri"], file_bytes, content_type)
    return client.table("s1_evidence_document").insert(row).execute().data[0]


# --- Append-only change log (immutable audit trail) -------------------------

def log_change(
    entity_table: str,
    entity_id: str,
    action: str,
    *,
    field_changes: dict | None = None,
    access_token: str,
    user_id: str,
) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {
        "org_id": org_id,
        "entity_table": entity_table,
        "entity_id": entity_id,
        "action": action,
        "field_changes": field_changes,
        "actor_id": user_id,
    }
    return client.table("s1_change_log").insert(row).execute().data[0]


def list_change_log(
    entity_table: str, entity_id: str, *, access_token: str, user_id: str
) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_change_log").select("*")
        .eq("org_id", org_id).eq("entity_table", entity_table).eq("entity_id", entity_id)
        .order("created_at").execute().data
    )


# --- OCR review queue -------------------------------------------------------

def create_ocr_extraction(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "created_by": user_id, **data}
    return client.table("s1_ocr_extraction").insert(row).execute().data[0]


def list_ocr_queue(
    *, status: str = "pending_review", access_token: str, user_id: str
) -> list[dict]:
    org_id, client = _org_and_client(access_token, user_id)
    return (
        client.table("s1_ocr_extraction").select("*")
        .eq("org_id", org_id).eq("status", status)
        .order("created_at").execute().data
    )


def get_ocr_extraction(extraction_id: str, *, access_token: str, user_id: str) -> dict | None:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_ocr_extraction").select("*")
        .eq("org_id", org_id).eq("id", extraction_id).limit(1).execute()
    )
    return resp.data[0] if resp.data else None


def update_ocr_extraction(extraction_id: str, patch: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    resp = (
        client.table("s1_ocr_extraction").update(patch)
        .eq("org_id", org_id).eq("id", extraction_id).execute()
    )
    return resp.data[0]


# --- Member roles -----------------------------------------------------------

def _default_role(org_member_role: str) -> str:
    """Org 'admin' -> Scope-1 admin; any other org member -> editor."""
    return "admin" if org_member_role == "admin" else "editor"


def get_scope1_role(*, access_token: str, user_id: str) -> str:
    """Resolve the caller's Scope-1 role in their active org (explicit row, else default)."""
    org_id, client = _org_and_client(access_token, user_id)
    explicit = (
        client.table("s1_member_role").select("role")
        .eq("org_id", org_id).eq("user_id", user_id).limit(1).execute()
    )
    if explicit.data:
        return explicit.data[0]["role"]
    org_member = (
        client.table("org_members").select("role")
        .eq("org_id", org_id).eq("user_id", user_id).limit(1).execute()
    )
    return _default_role(org_member.data[0]["role"] if org_member.data else "member")


def list_member_roles(*, access_token: str, user_id: str) -> list[dict]:
    """Org members with their resolved Scope-1 role (explicit row, else default)."""
    org_id, client = _org_and_client(access_token, user_id)
    members = (
        client.table("org_members").select("user_id, role")
        .eq("org_id", org_id).execute().data
    )
    explicit = {
        r["user_id"]: r["role"]
        for r in client.table("s1_member_role").select("user_id, role")
        .eq("org_id", org_id).execute().data
    }
    out = []
    for member in members:
        override = explicit.get(member["user_id"])
        out.append({
            "user_id": member["user_id"],
            "role": override or _default_role(member["role"]),
            "explicit": override is not None,
        })
    return out


def set_member_role(target_user_id: str, role: str, *, access_token: str, user_id: str) -> dict:
    """Upsert an explicit Scope-1 role for a member of the caller's active org."""
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "user_id": target_user_id, "role": role, "updated_by": user_id}
    return (
        client.table("s1_member_role")
        .upsert(row, on_conflict="org_id,user_id")
        .execute().data[0]
    )
