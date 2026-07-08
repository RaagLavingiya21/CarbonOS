"""Scope 1 process emissions — direct emissions from chemical / physical
transformation of materials (not combustion, not fugitive).

Pure, DB-free. Mirrors the combustion architecture: intake stores the emitted
*gas mass* (kg of CO2 / CH4 / N2O) computed as activity x process emission
factor — never CO2e. CO2e is derived at reporting time via the gas GWP for the
chosen AR version (reusing s1_calc.gwp), so the AR5/AR6 toggle works here too.

Examples: cement clinker (CO2 from calcination), lime, ammonia, glass, soda ash
(CO2), and nitric / adipic acid (N2O). A `custom` process lets a user supply
their own gas + factor.
"""

from s1_process.calc import compute_emission_kg, process_tco2e
from s1_process.factors import (
    PROCESS_FACTORS,
    PROCESS_GASES,
    UnknownProcess,
    get_process_factor,
    list_process_factors,
)

__all__ = [
    "PROCESS_FACTORS",
    "PROCESS_GASES",
    "UnknownProcess",
    "compute_emission_kg",
    "get_process_factor",
    "list_process_factors",
    "process_tco2e",
]
