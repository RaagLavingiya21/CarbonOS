"""Supabase CRUD for product volumes and corporate Scope 3 roll-up."""

from __future__ import annotations

from datetime import UTC, datetime

from calc.rollup import compute_rollup
from db.client import get_user_client
from db.org_store import get_active_org_member_ids
from db.reader import get_product_by_id, get_products_for_active_org
from db.store import _reporting_year

_VOLUME_COLUMNS = (
    "volume_id, product_lineage_id, user_id, year, annual_volume, unit, created_at, updated_at"
)


def _can_access_product(product: dict, user_id: str, access_token: str) -> bool:
    if product.get("user_id") == user_id:
        return True
    member_ids = get_active_org_member_ids(access_token, user_id=user_id)
    return bool(member_ids) and product.get("user_id") in member_ids


def _normalize_volume_row(row: dict) -> dict:
    return {
        "volume_id": row["volume_id"],
        "product_lineage_id": str(row["product_lineage_id"]),
        "user_id": str(row["user_id"]),
        "year": int(row["year"]),
        "annual_volume": float(row["annual_volume"]),
        "unit": row.get("unit") or "units",
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _per_unit_kg_co2e(product: dict) -> float:
    total_kg = float(product.get("total_kg_co2e") or 0)
    unitary_amount = float(product.get("unitary_product_amount") or 1)
    if unitary_amount:
        return total_kg / unitary_amount
    return total_kg


def _latest_published_per_lineage(products: list[dict]) -> list[dict]:
    by_lineage: dict[str, dict] = {}
    for product in products:
        lineage_id = str(product["product_lineage_id"])
        existing = by_lineage.get(lineage_id)
        if existing is None:
            by_lineage[lineage_id] = product
            continue
        if product.get("version", 0) > existing.get("version", 0):
            by_lineage[lineage_id] = product
            continue
        if product.get("version", 0) != existing.get("version", 0):
            continue
        pub_a = str(product.get("published_at") or "")
        pub_b = str(existing.get("published_at") or "")
        if pub_a > pub_b:
            by_lineage[lineage_id] = product
        elif pub_a == pub_b and product.get("product_id", 0) > existing.get("product_id", 0):
            by_lineage[lineage_id] = product
    return list(by_lineage.values())


def get_product_volume(
    product_id: int,
    *,
    year: int,
    user_id: str,
    access_token: str,
) -> dict | None:
    """Return the stored volume row for a product lineage and year, if any."""
    product = get_product_by_id(product_id, access_token)
    if product is None:
        return None
    if not _can_access_product(product, user_id, access_token):
        raise ValueError("Not authorized to access this product.")

    client = get_user_client(access_token)
    response = (
        client.table("product_volumes")
        .select(_VOLUME_COLUMNS)
        .eq("product_lineage_id", product["product_lineage_id"])
        .eq("year", year)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _normalize_volume_row(response.data[0])


def set_product_volume(
    product_id: int,
    *,
    year: int,
    annual_volume: float,
    unit: str,
    user_id: str,
    access_token: str,
) -> dict:
    """Upsert annual volume for a product lineage and reporting year."""
    if annual_volume < 0:
        raise ValueError("annual_volume must be greater than or equal to 0")

    product = get_product_by_id(product_id, access_token)
    if product is None:
        raise ValueError(f"Product {product_id} not found.")
    if not _can_access_product(product, user_id, access_token):
        raise ValueError("Not authorized to set volume for this product.")

    now = datetime.now(UTC).isoformat()
    payload = {
        "product_lineage_id": product["product_lineage_id"],
        "user_id": user_id,
        "year": year,
        "annual_volume": annual_volume,
        "unit": unit or "units",
        "updated_at": now,
    }

    client = get_user_client(access_token)
    response = (
        client.table("product_volumes")
        .upsert(payload, on_conflict="product_lineage_id,year")
        .select(_VOLUME_COLUMNS)
        .execute()
    )
    if not response.data:
        raise RuntimeError("Failed to save product volume.")
    return _normalize_volume_row(response.data[0])


def get_rollup(
    year: int,
    *,
    access_token: str,
    user_id: str,
) -> dict:
    """Build corporate Scope 3 Cat 1 roll-up for the active org and reporting year."""
    published = get_products_for_active_org(
        access_token,
        user_id=user_id,
        status="published",
    )
    latest = _latest_published_per_lineage(published)
    in_year = [
        product
        for product in latest
        if _reporting_year(product.get("reporting_period_start")) == year
    ]

    lineage_ids = [str(product["product_lineage_id"]) for product in in_year]
    volumes_by_lineage: dict[str, dict] = {}
    if lineage_ids:
        client = get_user_client(access_token)
        response = (
            client.table("product_volumes")
            .select(_VOLUME_COLUMNS)
            .in_("product_lineage_id", lineage_ids)
            .eq("year", year)
            .execute()
        )
        for row in response.data or []:
            volumes_by_lineage[str(row["product_lineage_id"])] = _normalize_volume_row(row)

    entries: list[dict] = []
    products_missing_volume: list[dict] = []
    for product in in_year:
        lineage_id = str(product["product_lineage_id"])
        volume_row = volumes_by_lineage.get(lineage_id)
        if volume_row is None:
            products_missing_volume.append(
                {
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                }
            )
            continue
        entries.append(
            {
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "per_unit_kg_co2e": _per_unit_kg_co2e(product),
                "annual_volume": volume_row["annual_volume"],
            }
        )

    rollup = compute_rollup(entries)
    return {
        **rollup,
        "year": year,
        "products_missing_volume": products_missing_volume,
    }
