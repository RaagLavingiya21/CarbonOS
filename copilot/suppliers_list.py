"""Workflow 1: Build a ranked list of supplier engagement candidates for a product.

Pure DB query — no LLM call. Matches line items to the suppliers contact table by
case-insensitive substring lookup on component name.

v1 known limitation: line_items has no supplier_id foreign key. Matching is
best-effort on component name. v2 will replace this with an explicit supplier_id
column in line_items.
"""

from __future__ import annotations

from db.copilot_store import get_engagements_for_product, get_supplier_by_name, get_all_suppliers
from db.reader import get_all_products, get_product_line_items
from copilot.models import EngagementCandidate, SuppliersListResult


def _match_supplier(
    component: str | None,
    material: str | None,
    access_token: str,
) -> tuple:
    """Try to match a component or material name to the suppliers table.

    Returns (supplier_name, contact_name, contact_email, contact_found).
    Tries component first, then material, then falls back to component name.
    """
    for candidate_name in filter(None, [component, material]):
        supplier = get_supplier_by_name(candidate_name, access_token)
        if supplier:
            return supplier.supplier_name, supplier.contact_name, supplier.contact_email, True

        for supplier_row in get_all_suppliers(access_token):
            name_lower = supplier_row.supplier_name.lower()
            comp_lower = candidate_name.lower()
            if comp_lower in name_lower or name_lower in comp_lower:
                return (
                    supplier_row.supplier_name,
                    supplier_row.contact_name,
                    supplier_row.contact_email,
                    True,
                )

    label = component or material or "Unknown"
    return label, None, None, False


def run(
    product_name: str,
    top_n: int = 5,
    *,
    access_token: str,
) -> SuppliersListResult:
    """Return the top-N highest-emitting engagement candidates for a product."""
    all_products = get_all_products(access_token)
    product = next(
        (product_row for product_row in all_products if product_row["product_name"].lower() == product_name.lower()),
        None,
    )
    if product is None:
        available = ", ".join(product_row["product_name"] for product_row in all_products) or "none"
        return SuppliersListResult(
            candidates=[],
            product_name=product_name,
            error=f"Product '{product_name}' not found. Available: {available}",
        )

    product_id = product["product_id"]
    canonical_name = product["product_name"]

    line_items = [
        line_item
        for line_item in get_product_line_items(product_id, access_token)
        if line_item["kg_co2e"] is not None
    ][:top_n]

    if not line_items:
        return SuppliersListResult(
            candidates=[],
            product_name=canonical_name,
            error="No matched line items found for this product.",
        )

    existing = {
        (engagement.supplier_name.lower(), (engagement.component_name or "").lower()): engagement
        for engagement in get_engagements_for_product(canonical_name, access_token)
    }

    candidates: list[EngagementCandidate] = []
    for line_item in line_items:
        supplier_name, contact_name, contact_email, contact_found = _match_supplier(
            line_item["component"], line_item["material"], access_token
        )

        key = (supplier_name.lower(), (line_item["component"] or "").lower())
        existing_eng = existing.get(key)

        candidates.append(
            EngagementCandidate(
                supplier_name=supplier_name,
                component=line_item["component"],
                material=line_item["material"],
                kg_co2e=line_item["kg_co2e"],
                share_pct=line_item["share_pct"],
                contact_found=contact_found,
                contact_name=contact_name,
                contact_email=contact_email,
                existing_engagement_id=existing_eng.engagement_id if existing_eng else None,
                engagement_status=existing_eng.status if existing_eng else "new",
            )
        )

    return SuppliersListResult(candidates=candidates, product_name=canonical_name)
