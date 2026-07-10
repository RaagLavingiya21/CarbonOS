"""DB-free tests for the Epic H use-phase route's pure calc helper."""

from __future__ import annotations

from api.models.scope3_schemas import UsePhaseCalcRequest
from api.routes.scope3_usephase import calc_from_request
from s3_usephase.factors import grid_ef


def test_direct_calc_matches_formula():
    body = UsePhaseCalcRequest(
        energy_per_use_kwh=0.5,
        uses_per_year=365,
        lifetime_years=10,
        units_sold=1000,
        region="USA",
        mode="direct",
        include_standby=False,
    )
    r = calc_from_request(body)
    expected = 1000 * 10 * 365 * 0.5 * grid_ef("USA")
    assert abs(r.kg_co2e - round(expected, 3)) < 1e-3
    assert r.method == "activity" and r.direct_or_indirect == "direct"


def test_indirect_calc_includes_water():
    body = UsePhaseCalcRequest(
        energy_per_use_kwh=0.6,
        water_l_per_use=15,
        uses_per_year=50,
        lifetime_years=3,
        units_sold=10000,
        region="EU",
        mode="indirect",
    )
    r = calc_from_request(body)
    assert r.direct_or_indirect == "indirect"
    assert r.breakdown["water_heating_kg"] > 0


def test_ef_source_flags_sample():
    body = UsePhaseCalcRequest(
        energy_per_use_kwh=0.5, uses_per_year=1, lifetime_years=1, units_sold=1, region="USA"
    )
    assert "SAMPLE" in calc_from_request(body).ef_source
