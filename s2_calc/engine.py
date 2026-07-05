"""Dual-method engine orchestration (PRD 5.4). MVP stub.

Phase M0 fills in:
  - location_based: sum(consumption_mwh x grid_average_factor) per site.
  - market_based: apply sourcing hierarchy (supplier-specific -> green tariff ->
    residual mix -> grid average, last resort flagged); net retired EAC/REC volume.
  - proration of irregular billing periods to the reporting year.
  - two labeled totals returned separately, plus the audit-log payload.

Depends on s2_factors and s2_sites (leaf). No UI or cross-scope imports.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DualMethodResult:
    location_based_kg_co2e: float
    market_based_kg_co2e: float
    reporting_year: int


def compute_dual_method(*args: object, **kwargs: object) -> DualMethodResult:
    """Compute location- and market-based totals. Implemented in Phase M0."""
    raise NotImplementedError(
        "s2_calc.engine.compute_dual_method is a Phase M0 deliverable."
    )
