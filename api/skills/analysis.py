"""Analysis skill — product footprint data queries."""

from __future__ import annotations

from typing import Any

from api.agent.intake_forms import get_intake_form
from api.skills.base import Skill
from db.org_store import get_active_org, get_active_org_member_ids
from db.reader import (
    get_all_products,
    get_product_by_id,
    get_product_by_name,
    get_product_line_items,
    get_products_for_active_org,
)

_HOTSPOT_LIMIT = 5


class AnalysisSkill(Skill):
    name = "analysis"
    description = (
        "Query saved product footprint analyses: list products, get details, "
        "identify emission hotspots, compare products, and launch the BOM Analyzer "
        "or Gap Analyzer modules with intake forms."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_products",
                    "get_product_details",
                    "get_hotspots",
                    "compare_products",
                    "launch_bom_analyzer",
                    "launch_gap_analyzer",
                ],
                "description": "The analysis operation to perform.",
            },
            "access_token": {
                "type": "string",
                "description": "Supabase access token for the authenticated user.",
            },
            "product_id": {
                "type": "integer",
                "description": "Product ID (for get_product_details or get_hotspots).",
            },
            "product_name": {
                "type": "string",
                "description": "Product name (for get_product_details or get_hotspots).",
            },
            "product_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Product names to compare (for compare_products).",
            },
            "product_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "Product IDs to compare (for compare_products).",
            },
            "limit": {
                "type": "integer",
                "description": "Max hotspots to return (default 5).",
            },
            "scope": {
                "type": "string",
                "enum": ["personal", "org"],
                "description": (
                    "Data scope: 'org' includes all team members' products (default when "
                    "user has an org); 'personal' restricts to the current user's products."
                ),
            },
            "user_id": {
                "type": "string",
                "description": "Authenticated user ID (injected by the agent).",
            },
        },
        "required": ["action", "access_token"],
    }

    async def run(self, action: str, **kwargs: Any) -> dict[str, Any]:
        handlers = {
            "list_products": self._list_products,
            "get_product_details": self._get_product_details,
            "get_hotspots": self._get_hotspots,
            "compare_products": self._compare_products,
            "launch_bom_analyzer": self._launch_bom_analyzer,
            "launch_gap_analyzer": self._launch_gap_analyzer,
        }
        handler = handlers.get(action)
        if handler is None:
            return _error(action, f"Unknown action: {action}")
        try:
            return handler(**kwargs)
        except Exception as exc:
            return _error(action, str(exc))

    def _list_products(
        self,
        *,
        access_token: str,
        scope: str | None = None,
        user_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        effective_scope = _resolve_scope(scope, access_token, user_id=user_id)
        if effective_scope == "personal":
            products = get_all_products(access_token, user_id=user_id)
        else:
            products = get_products_for_active_org(access_token, user_id=user_id)
        return _success(
            "list_products",
            {
                "scope": effective_scope,
                "count": len(products),
                "products": [_product_summary(p) for p in products],
            },
        )

    def _get_product_details(
        self,
        *,
        access_token: str,
        product_id: int | None = None,
        product_name: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        product = _resolve_product(access_token, product_id, product_name)
        if product is None:
            return _error(
                "get_product_details",
                "Product not found. Provide a valid product_id or product_name.",
            )
        return _success("get_product_details", {"product": _product_detail(product)})

    def _get_hotspots(
        self,
        *,
        access_token: str,
        product_id: int | None = None,
        product_name: str | None = None,
        limit: int = _HOTSPOT_LIMIT,
        **_: Any,
    ) -> dict[str, Any]:
        product = _resolve_product(access_token, product_id, product_name)
        if product is None:
            return _error(
                "get_hotspots",
                "Product not found. Provide a valid product_id or product_name.",
            )

        line_items = product.get("line_items") or get_product_line_items(
            product["product_id"], access_token
        )
        matched = [li for li in line_items if li.get("kg_co2e") is not None]
        matched.sort(key=lambda li: li.get("share_pct") or 0, reverse=True)
        top = matched[: max(limit, 1)]

        return _success(
            "get_hotspots",
            {
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "total_kg_co2e": product["total_kg_co2e"],
                "hotspot_count": len(top),
                "hotspots": [_line_item_summary(li) for li in top],
            },
        )

    def _compare_products(
        self,
        *,
        access_token: str,
        product_names: list[str] | None = None,
        product_ids: list[int] | None = None,
        scope: str | None = None,
        user_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        effective_scope = _resolve_scope(scope, access_token, user_id=user_id)
        if effective_scope == "personal":
            allowed_products = get_all_products(access_token, user_id=user_id)
        else:
            allowed_products = get_products_for_active_org(access_token, user_id=user_id)

        allowed_by_id = {p["product_id"]: p for p in allowed_products}
        allowed_by_name = {p["product_name"].lower(): p for p in allowed_products}

        names = product_names or []
        ids = product_ids or []
        if not names and not ids:
            return _error(
                "compare_products",
                "Provide product_names and/or product_ids to compare.",
            )

        products: list[dict] = []
        seen_ids: set[int] = set()

        for pid in ids:
            if pid in seen_ids:
                continue
            product = allowed_by_id.get(pid)
            if product:
                products.append(product)
                seen_ids.add(product["product_id"])

        for name in names:
            product = allowed_by_name.get(name.strip().lower())
            if product and product["product_id"] not in seen_ids:
                products.append(product)
                seen_ids.add(product["product_id"])

        if not products:
            return _error("compare_products", "No matching products found.")

        if len(products) < 2:
            return _error(
                "compare_products",
                "At least two products are required for comparison.",
            )

        sorted_by_total = sorted(
            products, key=lambda p: p.get("total_kg_co2e") or 0, reverse=True
        )
        highest = sorted_by_total[0]
        lowest = sorted_by_total[-1]

        return _success(
            "compare_products",
            {
                "scope": effective_scope,
                "product_count": len(products),
                "products": [_product_summary(p) for p in products],
                "highest_emitter": _product_summary(highest),
                "lowest_emitter": _product_summary(lowest),
                "delta_kg_co2e": round(
                    (highest.get("total_kg_co2e") or 0)
                    - (lowest.get("total_kg_co2e") or 0),
                    4,
                ),
            },
        )

    def _launch_bom_analyzer(self, **_: Any) -> dict[str, Any]:
        intake_form = get_intake_form("bom_analyzer")
        if intake_form is None:
            return _error("launch_bom_analyzer", "BOM Analyzer intake form not found.")
        return _success(
            "launch_bom_analyzer",
            {
                "module_launch": {
                    "module_type": "bom_analyzer",
                    "step": "intake",
                    "intake_form": intake_form,
                },
            },
        )

    def _launch_gap_analyzer(self, **_: Any) -> dict[str, Any]:
        intake_form = get_intake_form("gap_analyzer")
        if intake_form is None:
            return _error("launch_gap_analyzer", "Gap Analyzer intake form not found.")
        return _success(
            "launch_gap_analyzer",
            {
                "module_launch": {
                    "module_type": "gap_analyzer",
                    "step": "intake",
                    "intake_form": intake_form,
                },
            },
        )


def _resolve_scope(
    scope: str | None,
    access_token: str,
    *,
    user_id: str | None = None,
) -> str:
    """Default to org when the user has an active org; otherwise personal."""
    if scope in ("personal", "org"):
        return scope
    org = get_active_org(access_token, user_id=user_id)
    return "org" if org is not None else "personal"


def _resolve_product(
    access_token: str,
    product_id: int | None,
    product_name: str | None,
) -> dict | None:
    if product_id is not None:
        return get_product_by_id(product_id, access_token)
    if product_name:
        return get_product_by_name(product_name.strip(), access_token)
    return None


def _product_summary(product: dict) -> dict[str, Any]:
    return {
        "product_id": product["product_id"],
        "product_name": product["product_name"],
        "analysis_date": product.get("analysis_date"),
        "total_kg_co2e": product.get("total_kg_co2e"),
        "matched_items": product.get("matched_items"),
        "flagged_items": product.get("flagged_items"),
        "status": product.get("status"),
    }


def _product_detail(product: dict) -> dict[str, Any]:
    detail = _product_summary(product)
    detail["flagged_comment"] = product.get("flagged_comment")
    detail["line_items"] = [_line_item_summary(li) for li in product.get("line_items", [])]
    return detail


def _line_item_summary(line_item: dict) -> dict[str, Any]:
    return {
        "component": line_item.get("component"),
        "material": line_item.get("material"),
        "spend_usd": line_item.get("spend_usd"),
        "matched_sector": line_item.get("matched_sector"),
        "emission_factor": line_item.get("emission_factor"),
        "ef_source": line_item.get("ef_source"),
        "kg_co2e": line_item.get("kg_co2e"),
        "share_pct": line_item.get("share_pct"),
        "flag_status": line_item.get("flag_status"),
    }


def _success(action: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"action": action, "success": True, "data": data}


def _error(action: str, message: str) -> dict[str, Any]:
    return {"action": action, "success": False, "error": message}


analysis_skill = AnalysisSkill()
