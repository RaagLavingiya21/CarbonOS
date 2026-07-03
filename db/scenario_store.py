"""Supabase CRUD for scenario modeling (what-if footprint comparisons).

Tables (managed by supabase/migrations/023_scenarios.sql):
  scenarios           — user-owned scenario snapshots cloned from a baseline product
  scenario_line_items — editable line items with baseline reference values

Never writes to products or line_items.
"""

from __future__ import annotations

from db.client import get_user_client
from db.reader import get_product_by_id
from factors.ef_lookup import lookup_ef

_SCENARIO_COLUMNS = (
    "scenario_id, user_id, baseline_product_id, name, "
    "baseline_total_kg_co2e, total_kg_co2e, created_at"
)

_SCENARIO_ITEM_COLUMNS = (
    "scenario_item_id, scenario_id, user_id, component, material, spend_usd, "
    "matched_sector, emission_factor, ef_source, kg_co2e, share_pct, "
    "baseline_material, baseline_kg_co2e, is_edited"
)


def _compute_kg_co2e(
    spend_usd: float | None,
    emission_factor: float | None,
    *,
    is_no_match: bool = False,
) -> float:
    """Match calc/footprint.py _build_line_item spend × ef logic."""
    has_spend = spend_usd is not None and spend_usd > 0
    has_ef = emission_factor is not None and not is_no_match and emission_factor > 0
    if has_spend and has_ef:
        return round(spend_usd * emission_factor, 6)  # type: ignore[operator]
    return 0.0


def _recompute_shares(items: list[dict]) -> tuple[float, list[dict]]:
    """Recompute share_pct for all items; return (total_kg_co2e, updated items)."""
    total_kg_co2e = sum(li["kg_co2e"] for li in items if li.get("kg_co2e") is not None)
    for li in items:
        kg = li.get("kg_co2e")
        if kg is not None and total_kg_co2e > 0:
            li["share_pct"] = round(kg / total_kg_co2e * 100, 4)
        else:
            li["share_pct"] = None
    return round(total_kg_co2e, 6), items


def _scenario_item_row(
    scenario_id: int,
    user_id: str,
    li: dict,
    *,
    baseline_material: str | None = None,
    baseline_kg_co2e: float | None = None,
    is_edited: bool = False,
) -> dict:
    material = li.get("material")
    kg = li.get("kg_co2e")
    baseline_kg = baseline_kg_co2e
    if baseline_kg is None and kg is not None:
        baseline_kg = round(kg, 6)
    return {
        "scenario_id": scenario_id,
        "user_id": user_id,
        "component": li.get("component"),
        "material": material,
        "spend_usd": li.get("spend_usd"),
        "matched_sector": li.get("matched_sector"),
        "emission_factor": li.get("emission_factor"),
        "ef_source": li.get("ef_source"),
        "kg_co2e": round(kg, 6) if kg is not None else None,
        "share_pct": li.get("share_pct"),
        "baseline_material": baseline_material if baseline_material is not None else material,
        "baseline_kg_co2e": round(baseline_kg, 6) if baseline_kg is not None else None,
        "is_edited": is_edited,
    }


def _compute_deltas(scenario_total: float, baseline_total: float) -> tuple[float, float]:
    delta_kg = round(scenario_total - baseline_total, 6)
    delta_pct = round(delta_kg / baseline_total * 100, 4) if baseline_total > 0 else 0.0
    return delta_kg, delta_pct


def create_scenario_from_product(
    baseline_product_id: int,
    name: str,
    *,
    user_id: str,
    access_token: str,
) -> int:
    """Clone a baseline product into a new editable scenario."""
    baseline = get_product_by_id(baseline_product_id, access_token)
    if baseline is None:
        raise ValueError(f"Baseline product {baseline_product_id} not found.")

    baseline_total = float(baseline.get("total_kg_co2e") or 0.0)
    client = get_user_client(access_token)

    scenario_response = (
        client.table("scenarios")
        .insert(
            {
                "user_id": user_id,
                "baseline_product_id": baseline_product_id,
                "name": name,
                "baseline_total_kg_co2e": round(baseline_total, 6),
                "total_kg_co2e": round(baseline_total, 6),
            }
        )
        .execute()
    )
    scenario_id = int(scenario_response.data[0]["scenario_id"])

    line_items = baseline.get("line_items") or []
    item_rows = [
        _scenario_item_row(
            scenario_id,
            user_id,
            li,
            baseline_material=li.get("material"),
            baseline_kg_co2e=li.get("kg_co2e"),
            is_edited=False,
        )
        for li in line_items
    ]
    if item_rows:
        client.table("scenario_line_items").insert(item_rows).execute()

    return scenario_id


def _get_scenario_item(scenario_item_id: int, access_token: str) -> dict | None:
    client = get_user_client(access_token)
    response = (
        client.table("scenario_line_items")
        .select(_SCENARIO_ITEM_COLUMNS)
        .eq("scenario_item_id", scenario_item_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return response.data[0]


def _get_scenario_items(scenario_id: int, access_token: str) -> list[dict]:
    client = get_user_client(access_token)
    response = (
        client.table("scenario_line_items")
        .select(_SCENARIO_ITEM_COLUMNS)
        .eq("scenario_id", scenario_id)
        .order("share_pct", desc=True, nullsfirst=False)
        .execute()
    )
    return response.data


def edit_scenario_line_item(
    scenario_item_id: int,
    *,
    material: str | None = None,
    spend_usd: float | None = None,
    user_id: str,
    access_token: str,
) -> dict:
    """Edit a scenario line item's material and/or spend; recompute totals and shares."""
    item = _get_scenario_item(scenario_item_id, access_token)
    if item is None:
        raise ValueError(f"Scenario line item {scenario_item_id} not found.")

    scenario_id = int(item["scenario_id"])
    client = get_user_client(access_token)
    scenario_response = (
        client.table("scenarios")
        .select(_SCENARIO_COLUMNS)
        .eq("scenario_id", scenario_id)
        .limit(1)
        .execute()
    )
    if not scenario_response.data:
        raise ValueError(f"Scenario {scenario_id} not found.")
    scenario = scenario_response.data[0]
    baseline_total = float(scenario["baseline_total_kg_co2e"])

    updated = dict(item)
    material_changed = material is not None and material != item.get("material")
    is_no_match = False

    if material_changed:
        match = lookup_ef(material, None)  # type: ignore[arg-type]
        is_no_match = match.is_no_match
        updated["material"] = material
        updated["emission_factor"] = round(match.ef_kg_co2e_per_usd, 6) if not is_no_match else None
        updated["matched_sector"] = match.sector_name or None
        updated["ef_source"] = match.source_citation or None

    effective_spend = spend_usd if spend_usd is not None else updated.get("spend_usd")
    if spend_usd is not None:
        updated["spend_usd"] = spend_usd

    if material is not None or spend_usd is not None:
        updated["kg_co2e"] = _compute_kg_co2e(
            effective_spend,
            updated.get("emission_factor"),
            is_no_match=is_no_match if material_changed else False,
        )
        updated["is_edited"] = True

    client.table("scenario_line_items").update(
        {
            "material": updated.get("material"),
            "spend_usd": updated.get("spend_usd"),
            "matched_sector": updated.get("matched_sector"),
            "emission_factor": updated.get("emission_factor"),
            "ef_source": updated.get("ef_source"),
            "kg_co2e": updated.get("kg_co2e"),
            "is_edited": updated.get("is_edited", item.get("is_edited", False)),
        }
    ).eq("scenario_item_id", scenario_item_id).execute()

    all_items = _get_scenario_items(scenario_id, access_token)
    scenario_total, _ = _recompute_shares(all_items)

    for li in all_items:
        client.table("scenario_line_items").update({"share_pct": li.get("share_pct")}).eq(
            "scenario_item_id", li["scenario_item_id"]
        ).execute()

    client.table("scenarios").update({"total_kg_co2e": scenario_total}).eq(
        "scenario_id", scenario_id
    ).execute()

    delta_kg, delta_pct = _compute_deltas(scenario_total, baseline_total)
    edited_item = next(
        (li for li in all_items if int(li["scenario_item_id"]) == scenario_item_id),
        updated,
    )

    return {
        "scenario_total": scenario_total,
        "baseline_total": round(baseline_total, 6),
        "delta_kg": delta_kg,
        "delta_pct": delta_pct,
        "item": edited_item,
    }


def get_scenario(scenario_id: int, access_token: str) -> dict | None:
    """Return a scenario and its line items."""
    client = get_user_client(access_token)
    response = (
        client.table("scenarios")
        .select(_SCENARIO_COLUMNS)
        .eq("scenario_id", scenario_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None

    scenario = response.data[0]
    line_items = _get_scenario_items(scenario_id, access_token)
    scenario["line_items"] = line_items

    baseline_total = float(scenario["baseline_total_kg_co2e"])
    scenario_total = float(scenario["total_kg_co2e"])
    delta_kg, delta_pct = _compute_deltas(scenario_total, baseline_total)
    scenario["delta_kg"] = delta_kg
    scenario["delta_pct"] = delta_pct
    return scenario


def list_scenarios_for_product(baseline_product_id: int, access_token: str) -> list[dict]:
    """Return all scenarios cloned from a baseline product."""
    client = get_user_client(access_token)
    response = (
        client.table("scenarios")
        .select(_SCENARIO_COLUMNS)
        .eq("baseline_product_id", baseline_product_id)
        .order("created_at", desc=True)
        .execute()
    )
    results = []
    for row in response.data:
        baseline_total = float(row["baseline_total_kg_co2e"])
        scenario_total = float(row["total_kg_co2e"])
        delta_kg, delta_pct = _compute_deltas(scenario_total, baseline_total)
        row["delta_kg"] = delta_kg
        row["delta_pct"] = delta_pct
        results.append(row)
    return results


def delete_scenario(scenario_id: int, *, user_id: str, access_token: str) -> None:
    """Delete a scenario and its line items (cascade)."""
    client = get_user_client(access_token)
    existing = (
        client.table("scenarios")
        .select("scenario_id")
        .eq("scenario_id", scenario_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Scenario {scenario_id} not found.")
    client.table("scenarios").delete().eq("scenario_id", scenario_id).execute()
