"""Dataclasses for Category 11 use-phase (Epic H). DB-free.

Cat 11 is inherently ACTIVITY-based (there is no spend proxy for the energy a
product draws over its life), so results are labelled `method='activity'` and
must never be silently combined with spend-based totals.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProductEnergySpec:
    """Per-SKU energy/water spec (11.1) — from ENERGY STAR / EU label / eng data."""

    product_name: str
    energy_per_use_kwh: float = 0.0  # electricity per use (direct) or per activity (indirect)
    water_l_per_use: float = 0.0  # water heated per use (indirect: laundering/rinse)
    standby_power_w: float = 0.0  # continuous standby draw
    fuel_kwh_per_use: float = 0.0  # combusted fuel per use (gas appliances → direct GHG-in-use)
    spec_source: str = "manufacturer"


@dataclass
class UseProfile:
    """Usage intensity + lifetime (11.2)."""

    uses_per_year: float
    lifetime_years: float
    sub_sector: str = ""


@dataclass
class UsePhaseResult:
    product_name: str
    units_sold: float
    kg_co2e: float
    direct_or_indirect: str  # direct | indirect
    method: str = "activity"
    grid_basis: str = "location-based"
    ef_source: str = ""
    dq_note: str = ""
    breakdown: dict[str, float] = field(default_factory=dict)
