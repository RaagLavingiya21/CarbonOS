"""Location-based method (PRD 5.4): consumption x grid-average emission factor.

Leaf module — imports only the factor domain type.
"""

from __future__ import annotations

from s2_factors.library import EmissionFactor


def location_based_kg(consumption_mwh: float, factor: EmissionFactor) -> float:
    """kg CO2e = MWh x grid-average kg CO2e/MWh for the site's region + vintage."""
    return consumption_mwh * factor.kg_co2e_per_mwh
