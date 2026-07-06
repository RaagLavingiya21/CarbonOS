"""Market-based method with the GHG Protocol sourcing hierarchy (PRD 5.4).

For a site's consumption, quality-passing EACs cover load first (at their conveyed
rate — 0 for unbundled RECs). Load NOT covered by instruments is priced by the
highest available tier, and the engine may NOT drop to a lower tier when a higher
one exists:

    supplier-specific / green tariff  >  residual mix  >  grid average (flagged)

Grid-average fallback is flagged because it means residual-mix data was missing —
a data-quality gap, not a valid market-based source.

Leaf module — imports nothing internal (operates on primitives + EAC list).
"""

from __future__ import annotations

from dataclasses import dataclass

from s2_calc.models import EnergyAttributeCertificate


@dataclass(frozen=True)
class MarketResult:
    market_based_kg: float
    covered_mwh: float
    uncovered_mwh: float
    tier: str  # eac_covered | supplier_specific | residual_mix | grid_average_fallback
    fallback_flagged: bool


def market_based_site(
    consumption_mwh: float,
    valid_eacs: list[EnergyAttributeCertificate],
    *,
    supplier_specific_kg_per_mwh: float | None,
    residual_kg_per_mwh: float | None,
    grid_average_kg_per_mwh: float,
) -> MarketResult:
    """Market-based emissions for one site (kg CO2e).

    `valid_eacs` must already be quality-screened (see s2_calc.instruments).
    """
    remaining = consumption_mwh
    covered_mwh = 0.0
    covered_emissions = 0.0
    for eac in valid_eacs:
        if remaining <= 0:
            break
        allocated = min(eac.mwh, remaining)
        covered_emissions += allocated * eac.kg_co2e_per_mwh
        covered_mwh += allocated
        remaining -= allocated

    uncovered_mwh = max(remaining, 0.0)

    if uncovered_mwh == 0.0:
        tier = "eac_covered"
        fallback_flagged = False
        uncovered_emissions = 0.0
    elif supplier_specific_kg_per_mwh is not None:
        tier = "supplier_specific"
        fallback_flagged = False
        uncovered_emissions = uncovered_mwh * supplier_specific_kg_per_mwh
    elif residual_kg_per_mwh is not None:
        tier = "residual_mix"
        fallback_flagged = False
        uncovered_emissions = uncovered_mwh * residual_kg_per_mwh
    else:
        tier = "grid_average_fallback"
        fallback_flagged = True
        uncovered_emissions = uncovered_mwh * grid_average_kg_per_mwh

    return MarketResult(
        market_based_kg=covered_emissions + uncovered_emissions,
        covered_mwh=covered_mwh,
        uncovered_mwh=uncovered_mwh,
        tier=tier,
        fallback_flagged=fallback_flagged,
    )
