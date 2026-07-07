"""Refrigerant global-warming potentials (IPCC 100-year GWP, by AR version).

Pure-species GWPs are IPCC AR4 / AR5 / AR6 100-year values. Blend GWPs are
computed from component mass fractions at the same AR version (the standard
method), so a blend automatically tracks the AR toggle. Values are curated for
the common HVAC / refrigeration refrigerants; extend as needed.

Never store CO2e — these GWPs are applied at reporting time to the stored
leaked mass (kg) to derive tCO2e.
"""

from __future__ import annotations

AR_VERSIONS = ("AR4", "AR5", "AR6")


class UnknownRefrigerant(Exception):
    """Raised when a refrigerant is not in the library."""


# Pure species — canonical name -> {AR version: GWP100}.
_PURE: dict[str, dict[str, float]] = {
    "R-134a": {"AR4": 1430, "AR5": 1300, "AR6": 1526},   # HFC-134a
    "R-32": {"AR4": 675, "AR5": 677, "AR6": 771},        # HFC-32
    "R-125": {"AR4": 3500, "AR5": 3170, "AR6": 3740},    # HFC-125
    "R-143a": {"AR4": 4470, "AR5": 4800, "AR6": 5810},   # HFC-143a
    "R-152a": {"AR4": 124, "AR5": 138, "AR6": 164},      # HFC-152a
    "R-23": {"AR4": 14800, "AR5": 12400, "AR6": 14600},  # HFC-23
    "R-22": {"AR4": 1810, "AR5": 1760, "AR6": 1960},     # HCFC-22 (legacy)
    "R-12": {"AR4": 10900, "AR5": 10200, "AR6": 10200},  # CFC-12 (legacy)
    "SF6": {"AR4": 22800, "AR5": 23500, "AR6": 25200},
    "NF3": {"AR4": 17200, "AR5": 16100, "AR6": 17400},
    "R-744 (CO2)": {"AR4": 1, "AR5": 1, "AR6": 1},
    "R-717 (ammonia)": {"AR4": 0, "AR5": 0, "AR6": 0},
    "R-290 (propane)": {"AR4": 3, "AR5": 3, "AR6": 3},
}

# Blends — name -> {component species: mass fraction}. GWP computed from _PURE.
_BLENDS: dict[str, dict[str, float]] = {
    "R-410A": {"R-32": 0.50, "R-125": 0.50},
    "R-404A": {"R-125": 0.44, "R-134a": 0.04, "R-143a": 0.52},
    "R-407C": {"R-32": 0.23, "R-125": 0.25, "R-134a": 0.52},
    "R-507A": {"R-125": 0.50, "R-143a": 0.50},
}

REFRIGERANTS: tuple[str, ...] = tuple(_PURE) + tuple(_BLENDS)


def refrigerant_gwp(name: str, ar_version: str) -> float:
    """GWP100 for a refrigerant at the given AR version (kg CO2e per kg)."""
    ar = ar_version if ar_version in AR_VERSIONS else "AR5"
    if name in _PURE:
        return float(_PURE[name][ar])
    if name in _BLENDS:
        return float(sum(frac * _PURE[sp][ar] for sp, frac in _BLENDS[name].items()))
    raise UnknownRefrigerant(f"Unknown refrigerant: {name}")


def list_refrigerants() -> list[dict]:
    """All refrigerants with kind + GWP per AR version (for pickers / reference)."""
    out: list[dict] = []
    for name in _PURE:
        out.append({
            "name": name, "kind": "pure",
            "gwp": {ar: refrigerant_gwp(name, ar) for ar in AR_VERSIONS},
        })
    for name in _BLENDS:
        out.append({
            "name": name, "kind": "blend",
            "components": _BLENDS[name],
            "gwp": {ar: round(refrigerant_gwp(name, ar), 1) for ar in AR_VERSIONS},
        })
    return out
