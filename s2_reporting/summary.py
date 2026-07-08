"""Standard Scope 2 report summary (PRD 5.5).

Normalizes a persisted calculation into the canonical figures every destination
draws from — "one number, many formats." kg are converted to tCO2e (the unit CDP
and buyer templates expect). Pure — imports nothing internal.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReportSummary:
    entity: str
    reporting_year: int
    location_based_tco2e: float
    market_based_tco2e: float
    consumption_mwh: float
    data_coverage_pct: float
    methodology: str
    factor_versions: dict = field(default_factory=dict)
    # True when the market-based total fell back to grid/residual mix (no contractual
    # instruments) — the MB figure isn't substantiated by EACs. Drives compliance readiness.
    market_based_fallback: bool = False


def build_summary(
    calc: dict, *, entity: str, coverage_fraction: float
) -> ReportSummary:
    """Build the canonical summary from a calculation row + entity + coverage."""
    return ReportSummary(
        entity=entity,
        reporting_year=int(calc["reporting_year"]),
        location_based_tco2e=round(float(calc["location_based_kg_co2e"]) / 1000.0, 3),
        market_based_tco2e=round(float(calc["market_based_kg_co2e"]) / 1000.0, 3),
        consumption_mwh=round(float(calc.get("consumption_mwh") or 0.0), 3),
        data_coverage_pct=round(coverage_fraction * 100.0, 1),
        methodology=calc.get("methodology_notes")
        or "Dual-method (location + market-based) per GHG Protocol Scope 2.",
        factor_versions=calc.get("factor_versions") or {},
        market_based_fallback=bool(calc.get("market_fallback_flagged", False)),
    )
