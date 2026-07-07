"""Process-emission calculations (pure).

`compute_emission_kg` = activity x emission factor (kg gas). `process_tco2e`
converts a gas mass to tCO2e via the gas GWP at a given AR version, reusing the
canonical GWP table in s1_calc.gwp so process emissions track the AR toggle
exactly like combustion.
"""

from __future__ import annotations

from s1_calc import gwp_100


def compute_emission_kg(activity_quantity: float, ef_value: float) -> float:
    """Emitted gas mass (kg) = activity x emission factor."""
    if activity_quantity < 0 or ef_value < 0:
        raise ValueError("activity_quantity and ef_value must be non-negative.")
    return activity_quantity * ef_value


def process_tco2e(emission_kg: float, gas_species: str, ar_version: str) -> float:
    """tCO2e = emission_kg x GWP(gas, ar_version) / 1000 (kg -> tonne)."""
    return emission_kg * gwp_100(gas_species, ar_version) / 1000.0
