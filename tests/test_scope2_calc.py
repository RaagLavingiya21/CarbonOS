"""Scope 2 dual-method engine tests — hand-calc reconciliation (PRD 5.4 acceptance).

Factor values here are synthetic TEST FIXTURES, clearly labeled, never presented as
real eGRID/IEA/Green-e data. Real factors are seeded separately with citations.
"""

from __future__ import annotations

from datetime import date

import pytest

from s2_calc.engine import compute_dual_method
from s2_calc.instruments import QUALITY_CRITERIA, evaluate_quality, passes_all
from s2_calc.models import (
    ConsumptionRecord,
    EnergyAttributeCertificate,
    SiteProfile,
)
from s2_calc.proration import overlap_fraction, prorate_mwh
from s2_factors.library import (
    EmissionFactor,
    FactorLibrary,
    FactorNotFoundError,
)

GRID = 400.0  # TEST FIXTURE kg CO2e/MWh
RESIDUAL = 300.0  # TEST FIXTURE kg CO2e/MWh
REGION = "TEST_SUBREGION"
YEAR = 2022


def _library() -> FactorLibrary:
    return FactorLibrary(
        [
            EmissionFactor("egrid", REGION, YEAR, GRID, "TEST FIXTURE — not real eGRID"),
            EmissionFactor(
                "greene_residual", "US", YEAR, RESIDUAL, "TEST FIXTURE — not real Green-e"
            ),
        ]
    )


def _site(**kw) -> SiteProfile:
    base = dict(
        site_id="s1",
        location_factor_type="egrid",
        location_region=REGION,
        residual_factor_type="greene_residual",
        residual_region="US",
    )
    base.update(kw)
    return SiteProfile(**base)


def _bill(mwh: float, site_id: str = "s1") -> ConsumptionRecord:
    return ConsumptionRecord(
        site_id=site_id,
        energy_carrier="electricity",
        period_start=date(YEAR, 1, 1),
        period_end=date(YEAR, 12, 31),
        mwh=mwh,
    )


def _rec(mwh: float, site_id: str = "s1", **kw) -> EnergyAttributeCertificate:
    base = dict(
        instrument_id="rec1",
        site_id=site_id,
        instrument_type="rec",
        mwh=mwh,
        region_market=REGION,
        vintage_year=YEAR,
        kg_co2e_per_mwh=0.0,
    )
    base.update(kw)
    return EnergyAttributeCertificate(**base)


# --- proration -------------------------------------------------------------


def test_overlap_full_year() -> None:
    assert overlap_fraction(date(2022, 1, 1), date(2022, 12, 31), 2022) == 1.0


def test_overlap_split_across_year_boundary() -> None:
    # Dec 31 + Jan 1 = 2 inclusive days, 1 in 2022.
    assert prorate_mwh(2.0, date(2021, 12, 31), date(2022, 1, 1), 2022) == pytest.approx(1.0)


def test_overlap_outside_year_is_zero() -> None:
    assert overlap_fraction(date(2021, 1, 1), date(2021, 6, 1), 2022) == 0.0


# --- location-based --------------------------------------------------------


def test_location_based_hand_calc() -> None:
    result = compute_dual_method([_site()], [_bill(100)], [], _library(), YEAR)
    # 100 MWh x 400 kg/MWh = 40,000 kg
    assert result.location_based_kg_co2e == pytest.approx(40_000.0)


# --- market-based ----------------------------------------------------------


def test_market_based_fully_covered_by_recs_is_zero() -> None:
    result = compute_dual_method([_site()], [_bill(100)], [_rec(100)], _library(), YEAR)
    assert result.market_based_kg_co2e == pytest.approx(0.0)
    # Location-based is unaffected by instruments.
    assert result.location_based_kg_co2e == pytest.approx(40_000.0)


def test_market_based_partial_coverage_uses_residual() -> None:
    result = compute_dual_method([_site()], [_bill(100)], [_rec(60)], _library(), YEAR)
    # 40 uncovered MWh x 300 residual = 12,000 kg
    assert result.market_based_kg_co2e == pytest.approx(12_000.0)


def test_supplier_specific_beats_residual() -> None:
    site = _site(supplier_specific_kg_per_mwh=50.0)
    result = compute_dual_method([site], [_bill(100)], [], _library(), YEAR)
    # No EACs; uncovered 100 MWh must use supplier 50, not residual 300.
    assert result.market_based_kg_co2e == pytest.approx(5_000.0)
    assert result.site_results[0].market_tier == "supplier_specific"


def test_grid_fallback_is_flagged_when_no_residual() -> None:
    site = _site(residual_factor_type=None, residual_region=None)
    result = compute_dual_method([site], [_bill(100)], [], _library(), YEAR)
    assert result.site_results[0].market_fallback_flagged is True
    assert result.market_based_kg_co2e == pytest.approx(40_000.0)  # grid-average


def test_two_totals_are_distinct_never_merged() -> None:
    result = compute_dual_method([_site()], [_bill(100)], [_rec(100)], _library(), YEAR)
    assert result.location_based_kg_co2e != result.market_based_kg_co2e


# --- instrument quality criteria -------------------------------------------


def test_eight_criteria_present() -> None:
    assert len(QUALITY_CRITERIA) == 8


def test_wrong_market_rec_is_excluded_and_falls_to_residual() -> None:
    bad = _rec(100, region_market="OTHER_MARKET")
    result = compute_dual_method([_site()], [_bill(100)], [bad], _library(), YEAR)
    assert "rec1" in result.site_results[0].excluded_instruments
    # Excluded → all 100 MWh uncovered → residual 300.
    assert result.market_based_kg_co2e == pytest.approx(30_000.0)


def test_offset_rec_fails_quality() -> None:
    checks = evaluate_quality(_rec(10, not_an_offset=False), REGION, YEAR)
    assert checks["not_an_offset"] is False
    assert passes_all(checks) is False


def test_vintage_mismatch_fails_quality() -> None:
    checks = evaluate_quality(_rec(10, vintage_year=YEAR - 3), REGION, YEAR)
    assert checks["vintage_matched"] is False


# --- factor versioning -----------------------------------------------------


def test_factor_pins_to_latest_vintage_at_or_before_year() -> None:
    lib = FactorLibrary(
        [
            EmissionFactor("egrid", REGION, 2021, 500.0, "fixture"),
            EmissionFactor("egrid", REGION, 2023, 350.0, "fixture"),
        ]
    )
    assert lib.resolve("egrid", REGION, 2022).vintage_year == 2021
    assert lib.resolve("egrid", REGION, 2023).vintage_year == 2023
    assert lib.resolve("egrid", REGION, 2024).vintage_year == 2023


def test_factor_missing_before_earliest_vintage_raises() -> None:
    lib = FactorLibrary([EmissionFactor("egrid", REGION, 2021, 500.0, "fixture")])
    with pytest.raises(FactorNotFoundError):
        lib.resolve("egrid", REGION, 2020)


# --- rollup + audit --------------------------------------------------------


def test_multi_site_rollup_sums() -> None:
    sites = [_site(site_id="s1"), _site(site_id="s2")]
    bills = [_bill(100, "s1"), _bill(50, "s2")]
    result = compute_dual_method(sites, bills, [], _library(), YEAR)
    # (100 + 50) x 400 = 60,000
    assert result.location_based_kg_co2e == pytest.approx(60_000.0)
    assert len(result.site_results) == 2


def test_every_number_has_an_audit_trail() -> None:
    result = compute_dual_method([_site()], [_bill(100)], [], _library(), YEAR)
    assert len(result.audit_entries) == 1
    entry = result.audit_entries[0]
    assert entry["location_based"]["source_citation"]
    assert entry["location_based"]["formula"] == "consumption_mwh * kg_co2e_per_mwh"
    assert entry["location_based"]["kg_co2e"] == pytest.approx(40_000.0)
    # SiteResult also carries the factor citation for UI drill-down.
    assert result.site_results[0].location_factor_citation
