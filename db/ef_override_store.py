"""Supabase CRUD for org-wide and personal emission-factor overrides."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from db.client import get_user_client
from db.copilot_store import append_audit_log
from db.org_store import get_active_org
from factors.ef_lookup import get_all_sectors, normalize_material, search_sectors


@dataclass
class EFOverride:
    override_id: int
    org_id: str | None
    user_id: str
    material_normalized: str
    sector_code: str
    sector_name: str | None
    created_at: str
    updated_at: str


def _sector_name_for_code(sector_code: str) -> str | None:
    for code, name in get_all_sectors():
        if code == sector_code:
            return name
    return None


def get_active_overrides(access_token: str, *, user_id: str) -> dict[str, str]:
    """Return material_normalized → sector_code for the caller's active org or personal scope."""
    org = get_active_org(access_token, user_id=user_id)
    client = get_user_client(access_token)

    if org is not None:
        response = (
            client.table("ef_overrides")
            .select("material_normalized, sector_code")
            .eq("org_id", org.id)
            .execute()
        )
    else:
        response = (
            client.table("ef_overrides")
            .select("material_normalized, sector_code")
            .is_("org_id", "null")
            .eq("user_id", user_id)
            .execute()
        )

    return {
        str(row["material_normalized"]): str(row["sector_code"])
        for row in response.data
    }


def list_overrides(access_token: str, *, user_id: str) -> list[EFOverride]:
    """List overrides visible to the caller in their active org or personal scope."""
    org = get_active_org(access_token, user_id=user_id)
    client = get_user_client(access_token)

    if org is not None:
        response = (
            client.table("ef_overrides")
            .select("*")
            .eq("org_id", org.id)
            .order("material_normalized")
            .execute()
        )
    else:
        response = (
            client.table("ef_overrides")
            .select("*")
            .is_("org_id", "null")
            .eq("user_id", user_id)
            .order("material_normalized")
            .execute()
        )

    return [_override_from_row(row) for row in response.data]


def set_override(
    material: str,
    sector_code: str,
    sector_name: str | None,
    *,
    user_id: str,
    access_token: str,
) -> EFOverride:
    """Upsert a material→sector override for the active org or personal workspace."""
    material_normalized = normalize_material(material)
    if not material_normalized:
        raise ValueError("Material is required for an override.")

    resolved_sector_name = sector_name or _sector_name_for_code(sector_code)
    org = get_active_org(access_token, user_id=user_id)
    client = get_user_client(access_token)
    now = datetime.now(UTC).isoformat()

    payload = {
        "user_id": user_id,
        "material_normalized": material_normalized,
        "sector_code": sector_code,
        "sector_name": resolved_sector_name,
        "updated_at": now,
    }

    if org is not None:
        payload["org_id"] = org.id
        existing = (
            client.table("ef_overrides")
            .select("override_id")
            .eq("org_id", org.id)
            .eq("material_normalized", material_normalized)
            .limit(1)
            .execute()
        )
    else:
        payload["org_id"] = None
        existing = (
            client.table("ef_overrides")
            .select("override_id")
            .is_("org_id", "null")
            .eq("user_id", user_id)
            .eq("material_normalized", material_normalized)
            .limit(1)
            .execute()
        )

    if existing.data:
        override_id = int(existing.data[0]["override_id"])
        response = (
            client.table("ef_overrides")
            .update(payload)
            .eq("override_id", override_id)
            .execute()
        )
    else:
        payload["created_at"] = now
        response = client.table("ef_overrides").insert(payload).execute()

    override = _override_from_row(response.data[0])
    append_audit_log(
        event="ef_override_saved",
        workflow="factor_mapping",
        user_id=user_id,
        access_token=access_token,
        product_name=material_normalized,
        status=sector_code,
    )
    return override


def delete_override(override_id: int, *, user_id: str, access_token: str) -> None:
    """Delete an override row (RLS enforces org/personal scope)."""
    client = get_user_client(access_token)
    existing = (
        client.table("ef_overrides")
        .select("material_normalized, sector_code")
        .eq("override_id", override_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Override {override_id} not found.")

    client.table("ef_overrides").delete().eq("override_id", override_id).execute()
    row = existing.data[0]
    append_audit_log(
        event="ef_override_deleted",
        workflow="factor_mapping",
        user_id=user_id,
        access_token=access_token,
        product_name=str(row.get("material_normalized") or ""),
        status=str(row.get("sector_code") or ""),
    )


def search_sector_options(q: str | None = None, *, limit: int = 50) -> list[tuple[str, str]]:
    """Search CEDA sectors for the factor picker UI."""
    return search_sectors(q, limit=limit)


def _override_from_row(row: dict) -> EFOverride:
    return EFOverride(
        override_id=int(row["override_id"]),
        org_id=str(row["org_id"]) if row.get("org_id") else None,
        user_id=str(row["user_id"]),
        material_normalized=str(row["material_normalized"]),
        sector_code=str(row["sector_code"]),
        sector_name=row.get("sector_name"),
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    )
