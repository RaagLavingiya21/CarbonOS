"""Canonical EPA-anchored emission-factor set — the single source of truth.

The DB reference table `s1_ef_record` is seeded FROM this module
(scripts/seed_scope1_reference.py imports EPA_FACTORS), and the calc engine
reads it directly, so the stored factors and the computed factors can never
drift. Values verified against 40 CFR Part 98 Tables C-1/C-2 and the EPA
Emission Factors Hub 2025 (research/2.1).
"""

from __future__ import annotations

from s1_factors.models import EmissionFactor

EPA_HUB_VERSION = "2025-01-15"
EPA_HUB_URL = "https://www.epa.gov/climateleadership/ghg-emission-factors-hub"

# --- Stationary combustion: CO2 (Table C-1) + default HHV, CH4/N2O (Table C-2) ---
# fuel_or_activity, co2_kg_per_mmbtu, hhv, hhv_unit, ch4_n2o_category
_STATIONARY_FUELS = [
    ("natural_gas", 53.06, 1.026e-3, "mmBtu/scf", "natural_gas"),
    ("diesel_no2", 73.96, 0.138, "mmBtu/gal", "petroleum"),
    ("propane", 62.87, 0.091, "mmBtu/gal", "petroleum"),
    ("residual_oil_no6", 75.10, 0.150, "mmBtu/gal", "petroleum"),
    ("bituminous_coal", 93.28, 24.93, "mmBtu/ton", "coal"),
    ("subbituminous_coal", 97.17, 17.25, "mmBtu/ton", "coal"),
    ("anthracite", 103.69, 25.09, "mmBtu/ton", "coal"),
]
# CH4/N2O (kg/mmBtu) shared across the fuels in each category (Table C-2).
_STATIONARY_CH4_N2O = {
    "natural_gas": (1.0e-3, 1.0e-4),
    "petroleum": (3.0e-3, 6.0e-4),
    "coal": (1.1e-2, 1.6e-3),
    "solid_biomass": (3.2e-2, 4.2e-3),
    "gaseous_biomass": (3.2e-3, 6.3e-4),
}
# --- Mobile combustion: fuel-based CO2 (EPA Hub 2025 Table 2) ---
# fuel_or_activity, value, unit, biogenic
_MOBILE_CO2 = [
    ("motor_gasoline", 8.78, "kg/gal", False),
    ("diesel", 10.21, "kg/gal", False),
    ("lpg", 5.68, "kg/gal", False),
    ("cng", 0.05444, "kg/scf", False),
    ("lng", 4.50, "kg/gal", False),
    ("biodiesel_b100", 9.45, "kg/gal", True),
    ("ethanol_e100", 5.75, "kg/gal", True),
    ("jet_fuel", 9.75, "kg/gal", False),
]
# --- Mobile on-road CH4/N2O: distance-based, model-year specific (Tables 3-5) ---
# Core rows for the calc engine + golden-file evals; the full model-year matrix
# is ingested later by the s1_factors DB loader.
# fuel_or_activity, gas, value(g/mile), model_year
_MOBILE_DISTANCE = [
    ("gasoline_passenger_car", "CH4", 0.0050, 2022),
    ("gasoline_passenger_car", "N2O", 0.0014, 2022),
    ("gasoline_passenger_car", "N2O", 0.0600, 1995),  # older three-way-catalyst ~10x N2O
]


def _build() -> list[EmissionFactor]:
    factors: list[EmissionFactor] = []
    for fuel, co2, hhv, hhv_unit, cat in _STATIONARY_FUELS:
        factors.append(EmissionFactor(
            fuel, "stationary_combustion", "CO2", co2, "kg/mmBtu",
            source="40 CFR Part 98 Table C-1", source_version=EPA_HUB_VERSION,
            hhv=hhv, hhv_unit=hhv_unit))
        ch4, n2o = _STATIONARY_CH4_N2O[cat]
        factors.append(EmissionFactor(
            fuel, "stationary_combustion", "CH4", ch4, "kg/mmBtu",
            source="40 CFR Part 98 Table C-2", source_version=EPA_HUB_VERSION,
            hhv=hhv, hhv_unit=hhv_unit))
        factors.append(EmissionFactor(
            fuel, "stationary_combustion", "N2O", n2o, "kg/mmBtu",
            source="40 CFR Part 98 Table C-2", source_version=EPA_HUB_VERSION,
            hhv=hhv, hhv_unit=hhv_unit))
    for fuel, value, unit, biogenic in _MOBILE_CO2:
        factors.append(EmissionFactor(
            fuel, "mobile_combustion", "CO2", value, unit,
            source="EPA EF Hub 2025 Table 2", source_version=EPA_HUB_VERSION,
            biogenic=biogenic))
    for fuel, gas, value, model_year in _MOBILE_DISTANCE:
        factors.append(EmissionFactor(
            fuel, "mobile_onroad", gas, value, "g/mile",
            source="EPA EF Hub 2025 Tables 3-5", source_version=EPA_HUB_VERSION,
            model_year=model_year))
    return factors


EPA_FACTORS: list[EmissionFactor] = _build()
