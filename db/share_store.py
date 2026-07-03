"""Supabase CRUD for tokenized public footprint shares (Wave 2 Workstream S).

Public reads use the service-role client with share-token validation in code;
authenticated CRUD uses the user-scoped client (RLS owner policies).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from db.client import get_service_client, get_user_client
from db.copilot_store import append_audit_log
from db.reader import get_product_by_id
from exchange.pact import build_product_footprint, validate_product_footprint

_PRODUCT_COLUMNS = (
    "product_id, user_id, product_name, analysis_date, total_kg_co2e, "
    "matched_items, flagged_items, status, flagged_comment, footprint_uuid, "
    "product_description, declared_unit, unitary_product_amount, system_boundary, "
    "reporting_period_start, reporting_period_end, geography_country, "
    "primary_data_share, spec_version, version, product_lineage_id, published_at, "
    "technological_dqr, geographical_dqr, temporal_dqr, dqr_computed_at, "
    "submitted_for_review_by, submitted_at, reviewed_by, reviewed_at, review_comment, "
    "created_at, updated_at"
)

_LINE_ITEM_COLUMNS = (
    "item_id, component, material, spend_usd, matched_sector, emission_factor, "
    "ef_source, kg_co2e, share_pct, flag_status, data_source, ef_confidence, "
    "country_of_origin, technological_dqr, geographical_dqr, temporal_dqr"
)

_OWNER_FIELDS = frozenset(
    {
        "user_id",
        "submitted_for_review_by",
        "submitted_at",
        "reviewed_by",
        "reviewed_at",
        "review_comment",
        "flagged_comment",
    }
)


def create_share(
    product_id: int,
    *,
    recipient_label: str | None,
    user_id: str,
    access_token: str,
) -> dict:
    """Create a revocable share link for a published footprint owned by the caller."""
    product = get_product_by_id(product_id, access_token)
    if product is None:
        raise ValueError(f"Analysis {product_id} not found.")
    if product.get("status") != "published":
        raise ValueError("Only published footprints can be shared.")

    share_token = secrets.token_urlsafe(32)
    client = get_user_client(access_token)
    response = (
        client.table("footprint_shares")
        .insert(
            {
                "share_token": share_token,
                "product_id": product_id,
                "user_id": user_id,
                "recipient_label": recipient_label.strip() if recipient_label else None,
            }
        )
        .execute()
    )
    row = response.data[0]
    share_id = int(row["share_id"])

    append_audit_log(
        "share_created",
        "footprint_share",
        user_id=user_id,
        access_token=access_token,
        product_name=product.get("product_name"),
        status="active",
        decision_rationale=recipient_label.strip() if recipient_label else None,
    )

    return {"share_token": share_token, "share_id": share_id}


def list_shares_for_product(product_id: int, access_token: str) -> list[dict]:
    """Return share records for a product visible to the authenticated owner."""
    product = get_product_by_id(product_id, access_token)
    if product is None:
        raise ValueError(f"Analysis {product_id} not found.")

    client = get_user_client(access_token)
    response = (
        client.table("footprint_shares")
        .select("share_id, share_token, recipient_label, created_at, revoked_at")
        .eq("product_id", product_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def revoke_share(share_id: int, *, user_id: str, access_token: str) -> dict:
    """Revoke a share link owned by the caller."""
    client = get_user_client(access_token)
    lookup = (
        client.table("footprint_shares")
        .select("share_id, product_id, share_token, revoked_at")
        .eq("share_id", share_id)
        .limit(1)
        .execute()
    )
    if not lookup.data:
        raise ValueError(f"Share {share_id} not found.")
    row = lookup.data[0]
    if row.get("revoked_at") is not None:
        raise ValueError(f"Share {share_id} is already revoked.")

    revoked_at = datetime.now(UTC).isoformat()
    client.table("footprint_shares").update({"revoked_at": revoked_at}).eq(
        "share_id", share_id
    ).execute()

    product = get_product_by_id(int(row["product_id"]), access_token)
    append_audit_log(
        "share_revoked",
        "footprint_share",
        user_id=user_id,
        access_token=access_token,
        product_name=product.get("product_name") if product else None,
        status="revoked",
    )

    return {"share_id": share_id, "revoked_at": revoked_at}


def get_shared_footprint(share_token: str) -> dict | None:
    """Return a read-only public footprint view for a valid, non-revoked share token.

    Uses the service-role client; access control is the unguessable token plus a
    published footprint check. Owner identifiers are stripped from the response.
    """
    resolved = _resolve_active_share(share_token)
    if resolved is None:
        return None

    _share_row, product = resolved
    provenance = _build_public_provenance(product)
    return _strip_owner_fields(provenance)


def get_shared_pact_payload(share_token: str) -> dict | None:
    """Return a PACT v3 ProductFootprint payload for a valid public share token."""
    resolved = _resolve_active_share(share_token)
    if resolved is None:
        return None

    _share_row, product = resolved
    org_name, org_id = _org_context_for_product_owner(str(product["user_id"]))
    payload = build_product_footprint(product, org_name, org_id)
    violations = validate_product_footprint(payload)
    if violations:
        raise ValueError(f"PACT payload validation failed: {violations}")
    return payload


def _resolve_active_share(share_token: str) -> tuple[dict, dict] | None:
    """Look up a share by token and return (share_row, product_row) when valid."""
    client = get_service_client()
    share_response = (
        client.table("footprint_shares")
        .select("share_id, share_token, product_id, revoked_at")
        .eq("share_token", share_token)
        .limit(1)
        .execute()
    )
    if not share_response.data:
        return None

    share_row = share_response.data[0]
    if share_row.get("revoked_at") is not None:
        return None

    product_id = int(share_row["product_id"])
    product = _get_product_with_line_items(client, product_id)
    if product is None or product.get("status") != "published":
        return None

    return share_row, product


def _get_product_with_line_items(client, product_id: int) -> dict | None:
    response = (
        client.table("products")
        .select(_PRODUCT_COLUMNS)
        .eq("product_id", product_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None

    product = dict(response.data[0])
    analysis_date = product.get("analysis_date")
    if analysis_date is not None and not isinstance(analysis_date, str):
        product["analysis_date"] = str(analysis_date)

    line_items_response = (
        client.table("line_items")
        .select(_LINE_ITEM_COLUMNS)
        .eq("product_id", product_id)
        .order("share_pct", desc=True, nullsfirst=False)
        .execute()
    )
    product["line_items"] = line_items_response.data
    return product


def _build_public_provenance(product: dict) -> dict:
    """Mirror ``get_footprint_provenance`` output using data already loaded."""
    product_id = int(product["product_id"])
    client = get_service_client()
    lineage_id = product.get("product_lineage_id")
    version_rows: list[dict] = []
    if lineage_id:
        response = (
            client.table("products")
            .select(
                "product_id, version, status, analysis_date, published_at, created_at"
            )
            .eq("product_lineage_id", lineage_id)
            .order("version")
            .execute()
        )
        version_rows = response.data

    return {
        "product_id": product_id,
        "product_name": product.get("product_name"),
        "total_kg_co2e": product.get("total_kg_co2e"),
        "matched_items": product.get("matched_items"),
        "flagged_items": product.get("flagged_items"),
        "metadata": {
            "product_name": product.get("product_name"),
            "declared_unit": product.get("declared_unit"),
            "unitary_product_amount": product.get("unitary_product_amount"),
            "system_boundary": product.get("system_boundary"),
            "geography_country": product.get("geography_country"),
            "reporting_period_start": product.get("reporting_period_start"),
            "reporting_period_end": product.get("reporting_period_end"),
            "version": product.get("version"),
            "status": product.get("status"),
            "published_at": product.get("published_at"),
        },
        "method_statement": {
            "summary": "Spend-based Open CEDA 2025 screening assessment (kg CO₂e per USD spend).",
            "detail": (
                "Cradle-to-gate Scope 3 Category 1 footprint derived from bill-of-materials "
                "spend matched to Open CEDA 2025 emission factors. Screening-grade — not "
                "certification-ready."
            ),
        },
        "primary_data_share": product.get("primary_data_share"),
        "aggregate_dqr": {
            "technological": product.get("technological_dqr"),
            "geographical": product.get("geographical_dqr"),
            "temporal": product.get("temporal_dqr"),
            "computed_at": product.get("dqr_computed_at"),
        },
        "line_items": product.get("line_items") or [],
        "version_lineage": version_rows,
    }


def _org_context_for_product_owner(owner_user_id: str) -> tuple[str | None, str | None]:
    """Resolve org name/id for PACT export without exposing the owner user id."""
    client = get_service_client()
    membership = (
        client.table("org_members")
        .select("org_id")
        .eq("user_id", owner_user_id)
        .limit(1)
        .execute()
    )
    if not membership.data:
        return None, None

    org_id = str(membership.data[0]["org_id"])
    org_response = (
        client.table("organizations")
        .select("name")
        .eq("id", org_id)
        .limit(1)
        .execute()
    )
    org_name = org_response.data[0]["name"] if org_response.data else None
    return org_name, org_id


def _strip_owner_fields(payload: dict) -> dict:
    """Remove owner identifiers from a public footprint view."""
    cleaned = dict(payload)
    for field in _OWNER_FIELDS:
        cleaned.pop(field, None)

    metadata = cleaned.get("metadata")
    if isinstance(metadata, dict):
        cleaned["metadata"] = {
            key: value for key, value in metadata.items() if key not in _OWNER_FIELDS
        }

    line_items = cleaned.get("line_items")
    if isinstance(line_items, list):
        cleaned["line_items"] = [
            {key: value for key, value in item.items() if key not in _OWNER_FIELDS}
            for item in line_items
            if isinstance(item, dict)
        ]

    version_lineage = cleaned.get("version_lineage")
    if isinstance(version_lineage, list):
        cleaned["version_lineage"] = [
            {key: value for key, value in row.items() if key not in _OWNER_FIELDS}
            for row in version_lineage
            if isinstance(row, dict)
        ]

    return cleaned
