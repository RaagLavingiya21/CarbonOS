"""Supabase CRUD for the Scope 1 module (isolated from Carbon OS stores).

Every write is org-scoped: the active org (db.org_store.get_active_org) supplies
org_id, and RLS (is_org_member) enforces isolation. No UI imports. Reads return
plain dicts (mirroring db.reader). See supabase/migrations/030-036.
"""

from __future__ import annotations

from db.client import get_user_client
from db.org_store import get_active_org


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

def create_evidence(data: dict, *, access_token: str, user_id: str) -> dict:
    org_id, client = _org_and_client(access_token, user_id)
    row = {"org_id": org_id, "uploaded_by": user_id, **data}
    return client.table("s1_evidence_document").insert(row).execute().data[0]
