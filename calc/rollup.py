"""Corporate Scope 3 Category 1 roll-up aggregation (pure, no DB/UI imports)."""

from __future__ import annotations


def compute_rollup(entries: list[dict]) -> dict:
    """Sum per-product contributions into a corporate Scope 3 Cat 1 total.

    Each entry must include: product_id, product_name, per_unit_kg_co2e, annual_volume.
    Caller excludes products without volume before calling.
    """
    breakdown: list[dict] = []
    total = 0.0

    for entry in entries:
        per_unit = float(entry["per_unit_kg_co2e"])
        volume = float(entry["annual_volume"])
        contribution = per_unit * volume
        total += contribution
        breakdown.append(
            {
                "product_id": entry["product_id"],
                "product_name": entry["product_name"],
                "per_unit_kg_co2e": per_unit,
                "annual_volume": volume,
                "contribution_kg_co2e": contribution,
                "share_pct": 0.0,
            }
        )

    breakdown.sort(key=lambda row: row["contribution_kg_co2e"], reverse=True)

    if total > 0:
        for row in breakdown:
            row["share_pct"] = (row["contribution_kg_co2e"] / total) * 100.0

    return {
        "scope3_cat1_total_kg_co2e": total,
        "product_count": len(breakdown),
        "breakdown": breakdown,
    }
