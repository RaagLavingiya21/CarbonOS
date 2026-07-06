"""Documented estimation fallback for leased sites with no obtainable data (PRD 5.2).

When actual, landlord-provided, or benchmark-proxy data can't be had, estimate
annual electricity from floor area x a sector electricity-intensity benchmark,
clearly labeled as an estimate with the method + inputs recorded for audit
(GHG Protocol permits documented estimation).

The intensity defaults below are SAMPLE placeholders (order-of-magnitude), not
authoritative values — replace with CBECS / ENERGY STAR intensities before real
reporting. The per-estimate note always states the method, inputs, and that the
intensity is a replaceable default. Leaf module — imports nothing internal.
"""

from __future__ import annotations

from dataclasses import dataclass

# SAMPLE default electricity intensity (kWh per sqft per year) by site type.
# Replace with CBECS / ENERGY STAR values; every estimate records that these are
# placeholders. Site types match s2_sites.templates.SITE_TYPES.
_DEFAULT_KWH_PER_SQFT: dict[str, float] = {
    "retail": 14.0,
    "grocery": 50.0,  # refrigeration-heavy
    "food_service": 38.0,
    "manufacturing": 20.0,
    "warehouse_dc": 6.0,
    "office": 15.0,
}


@dataclass(frozen=True)
class EstimateResult:
    annual_mwh: float
    intensity_kwh_per_sqft: float
    method_note: str


class EstimationError(ValueError):
    """Raised when a site type has no benchmark or inputs are invalid."""


def estimate_annual_electricity_mwh(
    site_type: str, floor_area_sqft: float
) -> EstimateResult:
    """Estimate a site's annual electricity (MWh) from floor area x sector intensity."""
    if floor_area_sqft <= 0:
        raise EstimationError("floor_area_sqft must be positive.")
    key = site_type.strip().lower()
    intensity = _DEFAULT_KWH_PER_SQFT.get(key)
    if intensity is None:
        raise EstimationError(
            f"No electricity-intensity benchmark for site type '{site_type}'."
        )
    kwh = intensity * floor_area_sqft
    mwh = kwh / 1000.0
    note = (
        f"ESTIMATE: {floor_area_sqft:g} sqft x {intensity:g} kWh/sqft/yr "
        f"({key}, SAMPLE default electricity intensity — replace with CBECS/ENERGY STAR) "
        f"= {kwh:.0f} kWh = {mwh:.3f} MWh"
    )
    return EstimateResult(
        annual_mwh=mwh, intensity_kwh_per_sqft=intensity, method_note=note
    )
