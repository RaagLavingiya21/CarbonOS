"""EAC/REC quality-criteria checks (PRD 5.4; GHG Protocol Scope 2 Guidance).

Implements the 8 quality criteria a contractual instrument must meet to be usable
for market-based accounting (per research node L1.4). An instrument that fails any
criterion is excluded from market-based coverage and its load falls to residual
mix. `same_market` and `vintage_matched` are derived against the consuming site's
region and the reporting year; the rest are captured as evidence on the EAC.

Leaf module — imports only the s2_calc input model.
"""

from __future__ import annotations

from s2_calc.models import EnergyAttributeCertificate

# The 8 GHG Protocol Scope 2 quality criteria, in a stable order.
QUALITY_CRITERIA = (
    "specific_generation_attribute",
    "unique_no_double_count",
    "same_market",
    "registry_tracked",
    "retired_for_buyer",
    "vintage_matched",
    "not_an_offset",
    "transparent",
)


def evaluate_quality(
    eac: EnergyAttributeCertificate,
    site_region: str,
    reporting_year: int,
    *,
    vintage_tolerance_years: int = 0,
) -> dict[str, bool]:
    """Return a pass/fail map over all 8 criteria for one instrument."""
    return {
        "specific_generation_attribute": eac.specific_generation_attribute,
        "unique_no_double_count": eac.unique_no_double_count,
        "same_market": eac.region_market == site_region,
        "registry_tracked": eac.registry_tracked,
        "retired_for_buyer": eac.retired_for_buyer,
        "vintage_matched": abs(eac.vintage_year - reporting_year)
        <= vintage_tolerance_years,
        "not_an_offset": eac.not_an_offset,
        "transparent": eac.transparent,
    }


def passes_all(checks: dict[str, bool]) -> bool:
    """True only if every quality criterion passes."""
    return all(checks.values())
