"""Test expanded combustion source categories (residual oils, coal types, biomass)."""

import pytest

from s1_calc import calculate_stationary, to_co2e
from s1_factors import EmissionFactorLibrary
from s1_factors.epa_library import EPA_FACTORS


@pytest.fixture
def new_fuels():
    """Verify new fuel types are in the EPA factor library."""
    fuels = {f.fuel_or_activity for f in EPA_FACTORS if f.source_category == "stationary_combustion"}
    return fuels


def test_expanded_combustion_sources_present(new_fuels):
    """Verify all new combustion source categories are in the library."""
    expected = {
        # Residual fuel oils
        "residual_oil_no4", "residual_oil_no5", "residual_oil_no6",
        # Coal types
        "bituminous_coal", "subbituminous_coal", "anthracite", "lignite_coal",
        # Biomass
        "wood", "agricultural_residue",
        # Original fuels
        "natural_gas", "diesel_no2", "propane",
    }
    assert expected.issubset(new_fuels), f"Missing fuels: {expected - new_fuels}"


def test_residual_oil_no4_calculation():
    """Residual oil #4 (light residual) combustion factors resolve correctly."""
    lib = EmissionFactorLibrary(EPA_FACTORS)
    ef_co2 = lib.select("residual_oil_no4", "stationary_combustion", "CO2")
    assert ef_co2 is not None
    assert ef_co2.value == 75.15
    assert ef_co2.unit == "kg/mmBtu"
    # Test with actual calc
    result = calculate_stationary("residual_oil_no4", 100, "gallons", lib)
    assert result.gas_masses.kg_co2_fossil > 0
    tco2e_ar5 = to_co2e(result.gas_masses, "AR5")
    assert tco2e_ar5 > 0


def test_residual_oil_no5_calculation():
    """Residual oil #5 (medium residual) combustion factors resolve correctly."""
    lib = EmissionFactorLibrary(EPA_FACTORS)
    ef_co2 = lib.select("residual_oil_no5", "stationary_combustion", "CO2")
    assert ef_co2 is not None
    assert ef_co2.value == 75.12
    assert ef_co2.unit == "kg/mmBtu"


def test_lignite_coal_calculation():
    """Lignite coal combustion factors resolve and calculate correctly."""
    lib = EmissionFactorLibrary(EPA_FACTORS)
    ef_co2 = lib.select("lignite_coal", "stationary_combustion", "CO2")
    assert ef_co2 is not None
    assert ef_co2.value == 97.41
    assert ef_co2.unit == "kg/mmBtu"
    # Test with actual calc
    result = calculate_stationary("lignite_coal", 1, "tons", lib)
    assert result.gas_masses.kg_co2_fossil > 0
    tco2e_ar5 = to_co2e(result.gas_masses, "AR5")
    assert tco2e_ar5 > 0


def test_wood_combustion_biogenic_flag():
    """Wood combustion factor is marked biogenic in the EPA library."""
    wood_co2_factors = [f for f in EPA_FACTORS if f.fuel_or_activity == "wood" and f.gas == "CO2"]
    assert len(wood_co2_factors) > 0
    assert wood_co2_factors[0].biogenic is True, "Wood CO2 should be marked biogenic"


def test_agricultural_residue_biogenic_flag():
    """Agricultural residue combustion factor is marked biogenic in the EPA library."""
    ar_co2_factors = [f for f in EPA_FACTORS
                      if f.fuel_or_activity == "agricultural_residue" and f.gas == "CO2"]
    assert len(ar_co2_factors) > 0
    assert ar_co2_factors[0].biogenic is True, "Agricultural residue CO2 should be marked biogenic"


def test_wood_biogenic_calculation():
    """When explicitly marked biogenic=True, wood produces biogenic CO2."""
    lib = EmissionFactorLibrary(EPA_FACTORS)
    result = calculate_stationary("wood", 1, "tons", lib, biogenic=True)
    # When biogenic=True is passed, CO2 goes to biogenic bucket
    assert result.gas_masses.kg_co2_biogenic > 0
    assert result.gas_masses.kg_co2_fossil == 0.0


def test_petroleum_ch4_n2o_consistent():
    """All residual oils share the same CH4/N2O factors (petroleum category)."""
    ch4_factors = [f for f in EPA_FACTORS if f.gas == "CH4" and f.source_category == "stationary_combustion"]
    no4_ch4 = [f for f in ch4_factors if f.fuel_or_activity == "residual_oil_no4"]
    no5_ch4 = [f for f in ch4_factors if f.fuel_or_activity == "residual_oil_no5"]
    no6_ch4 = [f for f in ch4_factors if f.fuel_or_activity == "residual_oil_no6"]
    assert len(no4_ch4) > 0 and len(no5_ch4) > 0 and len(no6_ch4) > 0
    # All residual oils should have the same CH4 EF (same petroleum category)
    assert no4_ch4[0].value == no5_ch4[0].value == no6_ch4[0].value


def test_coal_types_ch4_n2o_consistent():
    """All coal types share the same CH4/N2O factors (coal category)."""
    ch4_factors = [f for f in EPA_FACTORS if f.gas == "CH4" and f.source_category == "stationary_combustion"]
    coal_types = ["bituminous_coal", "subbituminous_coal", "anthracite", "lignite_coal"]
    coal_ch4 = {ct: [f for f in ch4_factors if f.fuel_or_activity == ct][0] for ct in coal_types}
    # All coal types should have the same CH4 EF (same coal category)
    base_value = coal_ch4["bituminous_coal"].value
    for ct in coal_types:
        assert coal_ch4[ct].value == base_value, f"{ct} has different CH4 EF"


def test_factor_citations_present():
    """All new fuel factors have proper source citations."""
    new_fuel_factors = [f for f in EPA_FACTORS if f.fuel_or_activity in {
        "residual_oil_no4", "residual_oil_no5", "lignite_coal", "wood", "agricultural_residue"
    }]
    for factor in new_fuel_factors:
        assert factor.source is not None, f"Missing source for {factor.fuel_or_activity}"
        assert "40 CFR Part 98" in factor.source, f"Invalid source citation for {factor.fuel_or_activity}"
        assert factor.source_version is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
