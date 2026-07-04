"""Scope 1 emission-factor library (EPA-anchored, activity-based).

Isolated from the Carbon OS spend-based `factors/` module. Provides the EPA
Emission Factors Hub 2025 / 40 CFR Part 98 combustion factors and the selection
hierarchy over them. See research/2.1.
"""

from s1_factors.library import EmissionFactorLibrary
from s1_factors.models import EmissionFactor, MissingEmissionFactor

__all__ = ["EmissionFactor", "EmissionFactorLibrary", "MissingEmissionFactor"]
