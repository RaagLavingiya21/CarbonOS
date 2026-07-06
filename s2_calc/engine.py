"""Dual-method engine orchestration (PRD 5.4).

Given site profiles, normalized consumption, contractual instruments, and a
versioned factor library, produce two distinct labeled totals — location-based and
market-based — per site and rolled up, plus an audit payload per site so every
number traces to its source (PRD 5.6). The two totals are never merged or averaged.

Depends only on s2_factors and s2_calc siblings. No UI or cross-scope imports.
"""

from __future__ import annotations

from collections import defaultdict

from s2_calc.instruments import evaluate_quality, passes_all
from s2_calc.location_based import location_based_kg
from s2_calc.market_based import market_based_site
from s2_calc.models import (
    ConsumptionRecord,
    DualMethodResult,
    EnergyAttributeCertificate,
    SiteProfile,
    SiteResult,
)
from s2_calc.proration import prorate_mwh
from s2_factors.library import FactorLibrary


def compute_dual_method(
    sites: list[SiteProfile],
    consumption: list[ConsumptionRecord],
    instruments: list[EnergyAttributeCertificate],
    library: FactorLibrary,
    reporting_year: int,
    *,
    vintage_tolerance_years: int = 0,
) -> DualMethodResult:
    """Compute location- and market-based Scope 2 totals for a reporting year."""
    # Prorate consumption into the reporting year and total per site.
    mwh_by_site: dict[str, float] = defaultdict(float)
    for record in consumption:
        mwh_by_site[record.site_id] += prorate_mwh(
            record.mwh, record.period_start, record.period_end, reporting_year
        )

    instruments_by_site: dict[str, list[EnergyAttributeCertificate]] = defaultdict(list)
    for eac in instruments:
        instruments_by_site[eac.site_id].append(eac)

    total_location = 0.0
    total_market = 0.0
    site_results: list[SiteResult] = []
    audit_entries: list[dict] = []

    for site in sites:
        site_mwh = mwh_by_site.get(site.site_id, 0.0)

        # Location-based: grid-average factor for the site's region + vintage.
        grid_factor = library.resolve(
            site.location_factor_type, site.location_region, reporting_year
        )
        lb_kg = location_based_kg(site_mwh, grid_factor)

        # Screen instruments against the 8 quality criteria.
        valid_eacs: list[EnergyAttributeCertificate] = []
        excluded: list[str] = []
        eac_checks: dict[str, dict[str, bool]] = {}
        for eac in instruments_by_site.get(site.site_id, []):
            checks = evaluate_quality(
                eac,
                site.location_region,
                reporting_year,
                vintage_tolerance_years=vintage_tolerance_years,
            )
            eac_checks[eac.instrument_id] = checks
            if passes_all(checks):
                valid_eacs.append(eac)
            else:
                excluded.append(eac.instrument_id)

        # Market-based: EAC coverage first, then the highest available tier.
        residual_kg = None
        if site.residual_factor_type and site.residual_region:
            residual_kg = library.resolve(
                site.residual_factor_type, site.residual_region, reporting_year
            ).kg_co2e_per_mwh
        mb = market_based_site(
            site_mwh,
            valid_eacs,
            supplier_specific_kg_per_mwh=site.supplier_specific_kg_per_mwh,
            residual_kg_per_mwh=residual_kg,
            grid_average_kg_per_mwh=grid_factor.kg_co2e_per_mwh,
        )

        total_location += lb_kg
        total_market += mb.market_based_kg

        site_results.append(
            SiteResult(
                site_id=site.site_id,
                consumption_mwh=site_mwh,
                location_based_kg=lb_kg,
                market_based_kg=mb.market_based_kg,
                location_factor_citation=grid_factor.source_citation,
                location_factor_vintage=grid_factor.vintage_year,
                market_tier=mb.tier,
                market_fallback_flagged=mb.fallback_flagged,
                excluded_instruments=excluded,
            )
        )

        audit_entries.append(
            {
                "site_id": site.site_id,
                "reporting_year": reporting_year,
                "consumption_mwh": site_mwh,
                "location_based": {
                    "formula": "consumption_mwh * kg_co2e_per_mwh",
                    "factor_type": grid_factor.factor_type,
                    "factor_region": grid_factor.region_code,
                    "factor_vintage": grid_factor.vintage_year,
                    "kg_co2e_per_mwh": grid_factor.kg_co2e_per_mwh,
                    "source_citation": grid_factor.source_citation,
                    "kg_co2e": lb_kg,
                },
                "market_based": {
                    "tier": mb.tier,
                    "covered_mwh": mb.covered_mwh,
                    "uncovered_mwh": mb.uncovered_mwh,
                    "residual_kg_co2e_per_mwh": residual_kg,
                    "fallback_flagged": mb.fallback_flagged,
                    "kg_co2e": mb.market_based_kg,
                },
                "instrument_quality_checks": eac_checks,
                "excluded_instruments": excluded,
            }
        )

    return DualMethodResult(
        location_based_kg_co2e=total_location,
        market_based_kg_co2e=total_market,
        reporting_year=reporting_year,
        site_results=site_results,
        audit_entries=audit_entries,
    )
