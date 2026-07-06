"""Scope 1 per-gas combustion calc engine (activity-based, standards-grade).

Isolated from the Carbon OS spend-based `calc/` module. Outputs gas masses in kg
(never CO2e); CO2e is a reporting-layer transform via s1_calc.gwp. See research/2.1.
"""

from s1_calc.gwp import biogenic_co2e, gwp_100, to_co2e
from s1_calc.mobile import calculate_mobile
from s1_calc.models import CombustionResult, EmissionFactorRef, GasMasses
from s1_calc.stationary import calculate_stationary

__all__ = [
    "CombustionResult",
    "EmissionFactorRef",
    "GasMasses",
    "biogenic_co2e",
    "calculate_mobile",
    "calculate_stationary",
    "gwp_100",
    "to_co2e",
]
