"""Marginal abatement cost (MAC) curve (Epic I / P.3.5.b/.c). Pure, DB-free.

Ranks levers by $/tCO2e (cheapest first) and computes each lever's abatement
against the relevant category's emissions, plus a running cumulative total —
the classic MAC-curve ordering. Numbers are rough estimates (lever data), not a
full optimization; overlapping levers are treated independently (documented
limitation).
"""

from __future__ import annotations

from s3_levers.models import Lever, MACPoint


def build_mac_curve(levers: list[Lever], category_totals_tco2e: dict[int, float]) -> list[MACPoint]:
    """Return MACPoints sorted by ascending $/tCO2e with cumulative abatement.

    Args:
        levers: candidate levers.
        category_totals_tco2e: {scope3_category: tCO2e} from the inventory.
    """
    ranked = sorted(levers, key=lambda x: x.cost_per_tco2e)
    points: list[MACPoint] = []
    cumulative = 0.0
    for lev in ranked:
        base = category_totals_tco2e.get(lev.category, 0.0)
        abatement = base * lev.abatement_pct
        cumulative += abatement
        points.append(
            MACPoint(
                lever_id=lev.lever_id,
                name=lev.name,
                category=lev.category,
                abatement_tco2e=round(abatement, 3),
                cost_per_tco2e=lev.cost_per_tco2e,
                cumulative_abatement_tco2e=round(cumulative, 3),
            )
        )
    return points


def total_abatement_tco2e(points: list[MACPoint]) -> float:
    return round(sum(p.abatement_tco2e for p in points), 3)
