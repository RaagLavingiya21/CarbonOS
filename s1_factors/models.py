"""Data model for Scope 1 emission factors."""

from __future__ import annotations

from dataclasses import dataclass

# EF selection hierarchy ranks (research/2.1 section 4): a lower rank wins.
RANK_MEASURED = 1
RANK_SUPPLIER = 2
RANK_NATIONAL = 3  # EPA EF Hub / 40 CFR Part 98
RANK_REGIONAL = 4  # DEFRA (UK)
RANK_IPCC = 5      # IPCC default fallback


@dataclass(frozen=True)
class EmissionFactor:
    """A single gas emission factor. Never a CO2e factor — CO2e is derived later."""

    fuel_or_activity: str          # natural_gas|diesel_no2|motor_gasoline|...
    source_category: str           # stationary_combustion|mobile_combustion|mobile_onroad
    gas: str                       # CO2|CH4|N2O
    value: float
    unit: str                      # kg/mmBtu|kg/gal|kg/scf|g/mile
    source: str                    # '40 CFR Part 98 Table C-1' / 'EPA EF Hub 2025 Table 2'
    source_version: str            # '2025-01-15'
    region: str = "US"             # US|GB|GLOBAL
    tier: int = 1                  # 1|2|3
    biogenic: bool = False
    model_year: int | None = None  # mobile on-road distance EFs only
    hhv: float | None = None       # default higher heating value (energy per native unit)
    hhv_unit: str | None = None    # mmBtu/scf|mmBtu/gal|mmBtu/ton
    selection_rank: int = RANK_NATIONAL


class MissingEmissionFactor(Exception):
    """Raised when no active EF matches the requested fuel / category / gas."""
