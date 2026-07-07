"""Category 11 use-phase calculations (Epic H / 11.3 direct, 11.4 indirect).

Core formula: units_sold × lifetime × uses/year × energy(or water)/use ×
regional grid/water EF (+ direct GHG-in-use for fuel-burning products).
Pure logic, DB-free, deterministic. Results carry method='activity' and a DQ note.
"""

from __future__ import annotations

from s3_usephase.factors import FUEL_KG_PER_KWH, SAMPLE_EF_SOURCE, grid_ef, hot_water_ef
from s3_usephase.models import ProductEnergySpec, UsePhaseResult, UseProfile

_HOURS_PER_YEAR = 8760


def _total_uses(profile: UseProfile, units_sold: float) -> float:
    return units_sold * profile.lifetime_years * profile.uses_per_year


def direct_use_phase(
    spec: ProductEnergySpec,
    profile: UseProfile,
    units_sold: float,
    *,
    region: str | None = None,
    include_standby: bool = True,
) -> UsePhaseResult:
    """Direct use-phase (REQUIRED for energy-consuming products): the product's
    own electricity + any combusted fuel over its life."""
    uses = _total_uses(profile, units_sold)
    ef = grid_ef(region)

    electricity = uses * spec.energy_per_use_kwh * ef
    fuel = uses * spec.fuel_kwh_per_use * FUEL_KG_PER_KWH
    standby = 0.0
    if include_standby and spec.standby_power_w > 0:
        standby_kwh = (
            units_sold * profile.lifetime_years * (spec.standby_power_w / 1000) * _HOURS_PER_YEAR
        )
        standby = standby_kwh * ef

    total = electricity + fuel + standby
    return UsePhaseResult(
        product_name=spec.product_name,
        units_sold=units_sold,
        kg_co2e=round(total, 3),
        direct_or_indirect="direct",
        ef_source=SAMPLE_EF_SOURCE,
        dq_note="Activity-based; grid basis location-based (current grid, not projected).",
        breakdown={
            "electricity_kg": round(electricity, 3),
            "fuel_kg": round(fuel, 3),
            "standby_kg": round(standby, 3),
            "total_uses": uses,
        },
    )


def indirect_use_phase(
    spec: ProductEnergySpec,
    profile: UseProfile,
    units_sold: float,
    *,
    region: str | None = None,
) -> UsePhaseResult:
    """Indirect use-phase (OPTIONAL but recommended): energy/water for the
    associated activity — laundering a garment, heating water to rinse a
    shampoo, cooking a food product."""
    uses = _total_uses(profile, units_sold)
    activity_electricity = uses * spec.energy_per_use_kwh * grid_ef(region)
    water_heating = uses * spec.water_l_per_use * hot_water_ef(region)

    total = activity_electricity + water_heating
    return UsePhaseResult(
        product_name=spec.product_name,
        units_sold=units_sold,
        kg_co2e=round(total, 3),
        direct_or_indirect="indirect",
        ef_source=SAMPLE_EF_SOURCE,
        dq_note="Optional indirect use-phase (included); activity-based, location-based grid.",
        breakdown={
            "activity_electricity_kg": round(activity_electricity, 3),
            "water_heating_kg": round(water_heating, 3),
            "total_uses": uses,
        },
    )
