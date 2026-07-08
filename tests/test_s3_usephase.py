"""Tests for Epic H Category 11 use-phase (s3_usephase/). Pure logic.

Checks the core formula, direct vs indirect, standby, sub-sector templates,
the activity-method label, and determinism.
"""

from __future__ import annotations

import pytest

from s3_usephase.calc import direct_use_phase, indirect_use_phase
from s3_usephase.factors import grid_ef, hot_water_ef
from s3_usephase.models import ProductEnergySpec, UseProfile
from s3_usephase.templates import available_sub_sectors, get_template


def test_direct_matches_core_formula():
    # 1000 units × 10 yr × 365 uses × 0.5 kWh × 0.38 (USA) = 693,500 kg
    spec = ProductEnergySpec("Fridge", energy_per_use_kwh=0.5)
    profile = UseProfile(uses_per_year=365, lifetime_years=10)
    r = direct_use_phase(spec, profile, 1000, region="USA", include_standby=False)
    expected = 1000 * 10 * 365 * 0.5 * grid_ef("USA")
    assert r.kg_co2e == pytest.approx(round(expected, 3))
    assert r.method == "activity" and r.direct_or_indirect == "direct"


def test_standby_adds_when_included():
    spec = ProductEnergySpec("TV", energy_per_use_kwh=0.1, standby_power_w=5)
    profile = UseProfile(uses_per_year=300, lifetime_years=4)
    without = direct_use_phase(spec, profile, 100, region="EU", include_standby=False)
    with_sb = direct_use_phase(spec, profile, 100, region="EU", include_standby=True)
    assert with_sb.kg_co2e > without.kg_co2e
    assert with_sb.breakdown["standby_kg"] > 0


def test_fuel_using_product_has_direct_ghg():
    spec = ProductEnergySpec("Gas oven", fuel_kwh_per_use=1.2)
    r = direct_use_phase(spec, UseProfile(200, 12), 500, region="UK", include_standby=False)
    assert r.breakdown["fuel_kg"] > 0
    assert r.breakdown["electricity_kg"] == 0


def test_indirect_uses_water_heating():
    # Apparel laundering: water + electricity for the wash.
    spec = ProductEnergySpec("T-shirt", energy_per_use_kwh=0.6, water_l_per_use=15)
    r = indirect_use_phase(spec, UseProfile(50, 3), 10000, region="EU")
    assert r.direct_or_indirect == "indirect"
    assert r.breakdown["water_heating_kg"] > 0
    assert r.breakdown["activity_electricity_kg"] > 0


def test_hot_water_ef_scales_with_grid():
    assert hot_water_ef("CHINA") > hot_water_ef("EU")  # dirtier grid → higher


def test_templates_cover_subsectors_and_modes():
    assert set(available_sub_sectors()) == {
        "durables",
        "appliances",
        "apparel",
        "bpc",
        "electronics",
    }
    profile, mode = get_template("apparel")
    assert mode == "indirect" and profile.lifetime_years == 3
    _, dmode = get_template("durables")
    assert dmode == "direct"


def test_unknown_subsector_raises():
    with pytest.raises(KeyError):
        get_template("aerospace")


def test_ef_source_flags_sample_factors():
    spec = ProductEnergySpec("Fridge", energy_per_use_kwh=0.5)
    r = direct_use_phase(spec, UseProfile(365, 10), 1, region="USA")
    assert "SAMPLE" in r.ef_source


def test_determinism():
    spec = ProductEnergySpec("Fridge", energy_per_use_kwh=0.5)
    a = direct_use_phase(spec, UseProfile(365, 10), 1000, region="USA")
    b = direct_use_phase(spec, UseProfile(365, 10), 1000, region="USA")
    assert a.kg_co2e == b.kg_co2e
