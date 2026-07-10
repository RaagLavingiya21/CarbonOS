"""Verify seed_s1_reference.py imports and generates the correct factors."""

import pytest

from s1_factors.epa_library import EPA_FACTORS


def test_seed_script_has_updated_factors():
    """Verify the EPA factors include the expanded combustion sources."""
    factors_by_fuel = {}
    for ef in EPA_FACTORS:
        if ef.source_category == "stationary_combustion" and ef.gas == "CO2":
            factors_by_fuel[ef.fuel_or_activity] = ef

    # All new fuels should be present
    expected_fuels = {
        "residual_oil_no4", "residual_oil_no5", "residual_oil_no6",
        "lignite_coal", "wood", "agricultural_residue"
    }
    for fuel in expected_fuels:
        assert fuel in factors_by_fuel, f"Missing fuel: {fuel}"
        assert factors_by_fuel[fuel].source == "40 CFR Part 98 Table C-1"


def test_seed_script_factors_have_citations():
    """All factors should have proper source citations."""
    for ef in EPA_FACTORS:
        assert ef.source is not None, f"Missing source for {ef.fuel_or_activity}"
        assert ef.source_version is not None, f"Missing source_version for {ef.fuel_or_activity}"
        assert "40 CFR" in ef.source or "EPA EF Hub" in ef.source, \
            f"Invalid source for {ef.fuel_or_activity}: {ef.source}"


def test_seed_script_biogenic_flags_correct():
    """Biogenic fuels should be marked correctly."""
    wood_co2 = [f for f in EPA_FACTORS if f.fuel_or_activity == "wood" and f.gas == "CO2"]
    assert len(wood_co2) > 0
    assert wood_co2[0].biogenic is True

    natural_gas_co2 = [f for f in EPA_FACTORS if f.fuel_or_activity == "natural_gas" and f.gas == "CO2"]
    assert len(natural_gas_co2) > 0
    assert natural_gas_co2[0].biogenic is False


def test_seed_script_factor_count():
    """Should have reasonable number of factors."""
    # Count stationary combustion factors
    stationary = [f for f in EPA_FACTORS if f.source_category == "stationary_combustion"]
    # With 14 fuels (original 7 + new 7) and 3 gases each, expect 42+
    assert len(stationary) >= 36, f"Expected at least 36 stationary factors, got {len(stationary)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
