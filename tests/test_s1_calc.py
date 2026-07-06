"""Standards-correctness tests for the Scope 1 combustion calc engine.

Encodes the worked examples and invariants from research/2.1 and 2.2:
  - engine outputs gas masses (kg), never CO2e
  - CO2e is applied at reporting time; switching AR version does not mutate masses
  - biogenic CO2 is excluded from the S1 total (separate memo line)
  - vehicle model year drives N2O (~10x across fleet age)
  - every computed number carries EF provenance
"""

from __future__ import annotations

import dataclasses

import pytest

from s1_calc import (
    GasMasses,
    biogenic_co2e,
    calculate_mobile,
    calculate_stationary,
    gwp_100,
    to_co2e,
)
from s1_calc.units import to_mmbtu
from s1_factors import EmissionFactorLibrary, MissingEmissionFactor


@pytest.fixture
def lib() -> EmissionFactorLibrary:
    return EmissionFactorLibrary.default()


# --- Worked example A: 1,000 therms natural gas (stationary, fossil) ---------
def test_stationary_natural_gas_gas_masses(lib: EmissionFactorLibrary) -> None:
    r = calculate_stationary("natural_gas", 1000, "therms", lib)
    assert r.heat_input_mmbtu == pytest.approx(100.0)
    assert r.gas_masses.kg_co2_fossil == pytest.approx(5306.0, rel=1e-6)
    assert r.gas_masses.kg_ch4 == pytest.approx(0.100, rel=1e-6)
    assert r.gas_masses.kg_n2o == pytest.approx(0.010, rel=1e-6)
    assert r.gas_masses.kg_co2_biogenic == 0.0
    assert r.biogenic_fossil_tag == "fossil"
    # CO2e is a reporting transform, close to the raw CO2 mass (CO2 is ~99.9%).
    assert to_co2e(r.gas_masses, "AR5") == pytest.approx(5.31145, rel=1e-6)
    assert to_co2e(r.gas_masses, "AR6") == pytest.approx(5.31171, rel=1e-6)


# --- Worked example B: 1,000 gal diesel (stationary generator) ---------------
def test_stationary_diesel_via_hhv(lib: EmissionFactorLibrary) -> None:
    r = calculate_stationary("diesel_no2", 1000, "gal", lib)
    assert r.heat_input_mmbtu == pytest.approx(138.0)          # 1000 gal x 0.138 mmBtu/gal
    assert r.gas_masses.kg_co2_fossil == pytest.approx(10206.48, rel=1e-6)
    assert r.gas_masses.kg_ch4 == pytest.approx(0.414, rel=1e-6)
    assert r.gas_masses.kg_n2o == pytest.approx(0.0828, rel=1e-6)
    assert to_co2e(r.gas_masses, "AR5") == pytest.approx(10.24001, rel=1e-5)


# --- Worked example C: 10,000 mi gasoline car, 2022 MY, 400 gal --------------
def test_mobile_gasoline_car_2022(lib: EmissionFactorLibrary) -> None:
    r = calculate_mobile(
        "motor_gasoline", 400, "gal", lib,
        miles=10000, model_year=2022, distance_activity="gasoline_passenger_car",
    )
    assert r.gas_masses.kg_co2_fossil == pytest.approx(3512.0, rel=1e-6)
    assert r.gas_masses.kg_ch4 == pytest.approx(0.050, rel=1e-6)
    assert r.gas_masses.kg_n2o == pytest.approx(0.014, rel=1e-6)
    assert to_co2e(r.gas_masses, "AR5") == pytest.approx(3.51711, rel=1e-6)


def test_mobile_model_year_drives_n2o(lib: EmissionFactorLibrary) -> None:
    """Older three-way-catalyst vehicles emit ~10x N2O per mile."""
    new = calculate_mobile("motor_gasoline", 400, "gal", lib,
                           miles=10000, model_year=2022, distance_activity="gasoline_passenger_car")
    old = calculate_mobile("motor_gasoline", 400, "gal", lib,
                           miles=10000, model_year=1995, distance_activity="gasoline_passenger_car")
    assert old.gas_masses.kg_n2o > new.gas_masses.kg_n2o * 5
    assert old.gas_masses.kg_n2o == pytest.approx(0.600, rel=1e-6)  # 10000 x 0.06 g/mi / 1000


# --- Runtime GWP dispatch + no-mutation (R-410A refrigerant, research/2.2) ---
def test_gwp_runtime_dispatch_no_mutation() -> None:
    """25 kg HFC-32 + 25 kg HFC-125: AR5 96.2 tCO2e vs AR6 112.8 tCO2e from the
    SAME masses. Proves GWP is applied at reporting time, never stored."""
    ar5 = 25 * gwp_100("HFC-32", "AR5") + 25 * gwp_100("HFC-125", "AR5")
    ar6 = 25 * gwp_100("HFC-32", "AR6") + 25 * gwp_100("HFC-125", "AR6")
    assert ar5 / 1000 == pytest.approx(96.175, rel=1e-6)
    assert ar6 / 1000 == pytest.approx(112.775, rel=1e-6)
    assert ar6 > ar5  # ~17% higher under AR6


def test_ar_version_does_not_mutate_masses() -> None:
    masses = GasMasses(kg_co2_fossil=5306.0, kg_ch4=0.1, kg_n2o=0.01)
    snapshot = dataclasses.asdict(masses)
    _ = to_co2e(masses, "AR5")
    _ = to_co2e(masses, "AR6")
    assert dataclasses.asdict(masses) == snapshot


# --- Biogenic CO2 excluded from the S1 total (separate memo line) ------------
def test_biogenic_co2_excluded_from_total(lib: EmissionFactorLibrary) -> None:
    r = calculate_mobile("ethanol_e100", 100, "gal", lib)
    assert r.biogenic_fossil_tag == "biogenic"
    assert r.gas_masses.kg_co2_fossil == 0.0
    assert r.gas_masses.kg_co2_biogenic == pytest.approx(575.0, rel=1e-6)
    assert to_co2e(r.gas_masses, "AR5") == 0.0            # not in the S1 total
    assert biogenic_co2e(r.gas_masses, "AR5") == pytest.approx(0.575, rel=1e-6)  # memo line


# --- AR6 methane fossil/biogenic split --------------------------------------
def test_ar6_methane_fossil_biogenic_split() -> None:
    assert gwp_100("Methane", "AR6", "fossil") == 29.8
    assert gwp_100("Methane", "AR6", "biogenic") == 27.9
    assert gwp_100("Methane", "AR6") == 29.8              # combustion default = fossil
    assert gwp_100("Methane", "AR5") == 28.0


# --- Unit normalization ------------------------------------------------------
def test_unit_normalization() -> None:
    assert to_mmbtu(1000, "therms") == pytest.approx(100.0)
    assert to_mmbtu(100, "mmBtu") == pytest.approx(100.0)
    # 1 Ccf = 100 scf; NG default HHV 1.026e-3 mmBtu/scf -> 0.1026 mmBtu/Ccf.
    assert to_mmbtu(1000, "Ccf", hhv=1.026e-3) == pytest.approx(102.6, rel=1e-9)


# --- Traceability + missing-EF handling -------------------------------------
def test_every_number_carries_ef_provenance(lib: EmissionFactorLibrary) -> None:
    r = calculate_stationary("natural_gas", 1000, "therms", lib)
    assert len(r.ef_refs) == 3
    for ref in r.ef_refs:
        assert ref.source                       # non-empty citation
        assert "CFR" in ref.source or "EPA" in ref.source
        assert ref.source_version == "2025-01-15"


def test_missing_ef_raises(lib: EmissionFactorLibrary) -> None:
    with pytest.raises(MissingEmissionFactor):
        calculate_stationary("unobtanium", 100, "mmBtu", lib)


def test_determinism(lib: EmissionFactorLibrary) -> None:
    a = calculate_stationary("natural_gas", 1000, "therms", lib)
    b = calculate_stationary("natural_gas", 1000, "therms", lib)
    assert dataclasses.asdict(a.gas_masses) == dataclasses.asdict(b.gas_masses)
