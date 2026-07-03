"""Primary Data Share (PDS) computation — pure business logic, no DB/UI imports."""

from __future__ import annotations


def compute_primary_data_share(line_items: list[dict]) -> float:
    """Return the fraction of total kg CO₂e sourced from primary data.

    PDS = sum(kg_co2e where data_source == "primary") / sum(all kg_co2e),
    clamped to [0, 1]. Returns 0.0 when total is 0 or there are no primary items.
    """
    total = 0.0
    primary = 0.0
    for item in line_items:
        kg = item.get("kg_co2e")
        if kg is None:
            continue
        total += kg
        if item.get("data_source") == "primary":
            primary += kg
    if total == 0.0 or primary == 0.0:
        return 0.0
    return min(max(primary / total, 0.0), 1.0)
