"""Scope 1 fugitive emissions — refrigerant leakage from AC / refrigeration.

Pure, DB-free. Mirrors the combustion architecture: the intake stores a *leaked
mass* (kg of a refrigerant) — never CO2e — and CO2e is derived at reporting time
by applying the refrigerant's GWP for the chosen AR version. So the AR5/AR6
toggle works for fugitive emissions exactly as it does for combustion.

Two estimation methods (IPCC / GHG Protocol):
  - screening: annual leak = charge x annual leak rate (%),
  - material_balance: leak = purchases + beginning stock - ending stock.
"""

from s1_fugitive.calc import FugitiveResult, compute_leaked_kg, fugitive_tco2e
from s1_fugitive.refrigerants import (
    REFRIGERANTS,
    UnknownRefrigerant,
    list_refrigerants,
    refrigerant_gwp,
)

__all__ = [
    "REFRIGERANTS",
    "FugitiveResult",
    "UnknownRefrigerant",
    "compute_leaked_kg",
    "fugitive_tco2e",
    "list_refrigerants",
    "refrigerant_gwp",
]
