"""Grid / water-heating emission factors for Cat 11 (Epic H).

SAMPLE VALUES ONLY — clearly labelled. Real reporting must license authoritative
factors (IEA, EPA eGRID, DEFRA, AIB) per the research build-vs-buy call. These
are order-of-magnitude placeholders so the calc runs end-to-end.
"""

from __future__ import annotations

# Location-based grid intensity, kg CO2e per kWh (sample, ~2024 order of magnitude).
_GRID_KG_PER_KWH: dict[str, float] = {
    "USA": 0.38,
    "EU": 0.25,
    "UK": 0.21,
    "CHINA": 0.58,
    "INDIA": 0.71,
    "GLOBAL": 0.48,
}
_DEFAULT_REGION = "GLOBAL"

# Combusted fuel (natural gas) for gas appliances, kg CO2e per kWh (sample).
FUEL_KG_PER_KWH = 0.18

# Energy to heat 1 L of water ~0.046 kWh (ΔT ~40°C); combined with grid EF.
_KWH_PER_LITRE_HEATED = 0.046

SAMPLE_EF_SOURCE = "SAMPLE grid/water factors (replace with IEA/eGRID/DEFRA for reporting)"


def grid_ef(region: str | None) -> float:
    """kg CO2e per kWh for a region (case-insensitive), default GLOBAL."""
    return _GRID_KG_PER_KWH.get(
        (region or _DEFAULT_REGION).upper(), _GRID_KG_PER_KWH[_DEFAULT_REGION]
    )


def hot_water_ef(region: str | None) -> float:
    """kg CO2e per litre of water heated (electric heating on the regional grid)."""
    return _KWH_PER_LITRE_HEATED * grid_ef(region)
