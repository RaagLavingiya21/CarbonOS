"""Read-only queries for the conversational advisor and gap analyzer.

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from db.client import get_user_client

_PRODUCT_COLUMNS = (
    "product_id, user_id, product_name, analysis_date, total_kg_co2e, "
    "matched_items, flagged_items, status, flagged_comment"
)

_LINE_ITEM_COLUMNS = (
    "component, material, spend_usd, matched_sector, emission_factor, "
    "ef_source, kg_co2e, share_pct, flag_status"
)


def get_all_products(
    access_token: str,
    *,
    user_id: str | None = None,
    member_user_ids: list[str] | None = None,
) -> list[dict]:
    """Return product rows for the authenticated user (RLS-scoped).

    When user_id is provided, restrict to that user's products (personal scope).
    When member_user_ids is provided, restrict to those org members (org scope).
    """
    client = get_user_client(access_token)
    query = client.table("products").select(_PRODUCT_COLUMNS)
    if user_id is not None:
        query = query.eq("user_id", user_id)
    elif member_user_ids:
        query = query.in_("user_id", member_user_ids)
    response = query.order("analysis_date", desc=True).execute()
    return [_normalize_product_row(row) for row in response.data]


def get_products_for_active_org(access_token: str, *, user_id: str | None = None) -> list[dict]:
    """Return products visible in the user's active workspace org."""
    from db.org_store import get_active_org_member_ids

    member_ids = get_active_org_member_ids(access_token, user_id=user_id)
    if not member_ids:
        return get_all_products(access_token, user_id=user_id)
    return get_all_products(access_token, member_user_ids=member_ids)


def get_product_by_name(name: str, access_token: str) -> dict | None:
    """Return a product summary and line items by name (most recent match)."""
    client = get_user_client(access_token)
    response = (
        client.table("products")
        .select(_PRODUCT_COLUMNS)
        .eq("product_name", name)
        .order("analysis_date", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    product = _normalize_product_row(response.data[0])
    product["line_items"] = get_product_line_items(product["product_id"], access_token)
    return product


def get_product_by_id(product_id: int, access_token: str) -> dict | None:
    """Return a product summary and line items by product ID."""
    client = get_user_client(access_token)
    response = (
        client.table("products")
        .select(_PRODUCT_COLUMNS)
        .eq("product_id", product_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    product = _normalize_product_row(response.data[0])
    product["line_items"] = get_product_line_items(product_id, access_token)
    return product


def get_product_line_items(product_id: int, access_token: str) -> list[dict]:
    """Return all line items for a product."""
    client = get_user_client(access_token)
    response = (
        client.table("line_items")
        .select(_LINE_ITEM_COLUMNS)
        .eq("product_id", product_id)
        .order("share_pct", desc=True, nullsfirst=False)
        .execute()
    )
    return response.data


def build_llm_context(access_token: str, *, user_id: str | None = None) -> str:
    """Build a text summary of saved analyses for the LLM system prompt."""
    products = get_products_for_active_org(access_token, user_id=user_id)

    if not products:
        return "No product analyses have been saved yet."

    lines: list[str] = ["## Saved Product Footprint Analyses\n"]

    for product in products:
        lines.append(
            f"### Product: {product['product_name']} (ID: {product['product_id']})\n"
            f"- Analysis date: {product['analysis_date']}\n"
            f"- Total footprint: {product['total_kg_co2e']:.4f} kg CO₂e\n"
            f"- Matched line items: {product['matched_items']}\n"
            f"- Flagged line items: {product['flagged_items']}\n"
        )

        items = get_product_line_items(product["product_id"], access_token)
        if items:
            lines.append("#### Line items (sorted by share, highest first):\n")
            for li in items:
                component = li["component"] or "—"
                material = li["material"] or "—"
                spend = f"${li['spend_usd']:.2f}" if li["spend_usd"] is not None else "—"
                sector = li["matched_sector"] or "unmatched"
                ef = f"{li['emission_factor']:.6f}" if li["emission_factor"] is not None else "—"
                kg = f"{li['kg_co2e']:.4f}" if li["kg_co2e"] is not None else "—"
                share = f"{li['share_pct']:.1f}%" if li["share_pct"] is not None else "—"
                flag = li["flag_status"]
                lines.append(
                    f"- {component} / {material}: spend={spend}, sector={sector}, "
                    f"EF={ef} kgCO₂e/USD, footprint={kg} kg CO₂e, share={share}, status={flag}"
                )
            lines.append("")

    return "\n".join(lines)


def _normalize_product_row(row: dict) -> dict:
    """Ensure analysis_date is a string for API compatibility."""
    normalized = dict(row)
    analysis_date = normalized.get("analysis_date")
    if analysis_date is not None and not isinstance(analysis_date, str):
        normalized["analysis_date"] = str(analysis_date)
    return normalized
