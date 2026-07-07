"""Year-over-year trend + emissions-intensity analysis (pure, DB-free).

`build_trends` takes each inventory's already-rolled-up Scope 1 total (from the
reporting engine, at a chosen GWP/AR version) plus its operational denominators
(revenue / output / headcount) and produces:
  - a year-sorted series with year-over-year absolute & % change, and
  - intensity metrics per year (tCO2e per $M revenue / per output unit / per FTE),
  - a comparison of the latest year against the declared base year.

CO2e is never stored — the totals are passed in already derived at reporting
time, so this stays a pure transform (matches the rest of s1_reporting).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryDatum:
    """One inventory's total + operational denominators."""

    inventory_id: str
    reporting_year: int
    total_tco2e: float
    annual_revenue: float | None = None      # native currency, absolute
    revenue_currency: str = "USD"
    output_quantity: float | None = None
    output_unit: str | None = None
    headcount: int | None = None


@dataclass(frozen=True)
class TrendPoint:
    inventory_id: str
    reporting_year: int
    total_tco2e: float
    is_base_year: bool
    yoy_abs: float | None            # vs the previous year in the series
    yoy_pct: float | None
    # Intensities (None when the denominator is missing / zero):
    per_revenue_mm: float | None     # tCO2e per $1M revenue
    revenue_currency: str
    per_output: float | None         # tCO2e per output unit
    output_unit: str | None
    per_headcount: float | None      # tCO2e per FTE


@dataclass(frozen=True)
class TrendsResult:
    ar_version: str
    points: list[TrendPoint]         # ascending by reporting_year
    base_year: int | None
    base_year_total_tco2e: float | None
    latest_vs_base_abs: float | None
    latest_vs_base_pct: float | None


def _pct(delta: float, base: float) -> float | None:
    return (delta / base * 100.0) if base else None


def _intensity(total: float, denom: float | None) -> float | None:
    if denom is None or denom == 0:
        return None
    return total / denom


def build_trends(
    data: list[InventoryDatum],
    *,
    ar_version: str,
    base_year: int | None = None,
    base_year_total_tco2e: float | None = None,
) -> TrendsResult:
    ordered = sorted(data, key=lambda d: d.reporting_year)
    points: list[TrendPoint] = []
    prev_total: float | None = None
    for d in ordered:
        yoy_abs = (d.total_tco2e - prev_total) if prev_total is not None else None
        yoy_pct = _pct(yoy_abs, prev_total) if (yoy_abs is not None and prev_total is not None) else None
        points.append(
            TrendPoint(
                inventory_id=d.inventory_id,
                reporting_year=d.reporting_year,
                total_tco2e=d.total_tco2e,
                is_base_year=(base_year is not None and d.reporting_year == base_year),
                yoy_abs=yoy_abs,
                yoy_pct=yoy_pct,
                per_revenue_mm=_intensity(
                    d.total_tco2e,
                    (d.annual_revenue / 1_000_000.0) if d.annual_revenue else None,
                ),
                revenue_currency=d.revenue_currency,
                per_output=_intensity(d.total_tco2e, d.output_quantity),
                output_unit=d.output_unit,
                per_headcount=_intensity(
                    d.total_tco2e, float(d.headcount) if d.headcount else None
                ),
            )
        )
        prev_total = d.total_tco2e

    latest_abs = latest_pct = None
    if points and base_year_total_tco2e is not None:
        latest_abs = points[-1].total_tco2e - base_year_total_tco2e
        latest_pct = _pct(latest_abs, base_year_total_tco2e)

    return TrendsResult(
        ar_version=ar_version,
        points=points,
        base_year=base_year,
        base_year_total_tco2e=base_year_total_tco2e,
        latest_vs_base_abs=latest_abs,
        latest_vs_base_pct=latest_pct,
    )
