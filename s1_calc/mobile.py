"""Mobile combustion calc.

    CO2  = fuel-based:     fuel_qty × EF_CO2   (kg/gal or kg/scf)
    CH4  = distance-based: miles × EF_CH4(g/mi) × 0.001   (on-road, model-year specific)
    N2O  = distance-based: miles × EF_N2O(g/mi) × 0.001

N2O varies ~10x across fleet age, so model year is required for the distance EFs.
Outputs gas masses only. See research/2.1 section 2.
"""

from __future__ import annotations

from s1_calc.models import CombustionResult, EmissionFactorRef, GasMasses
from s1_factors.library import EmissionFactorLibrary

G_PER_MILE_TO_KG = 0.001


def calculate_mobile(
    fuel_or_activity: str,
    fuel_quantity: float,
    fuel_unit: str,
    library: EmissionFactorLibrary,
    *,
    miles: float | None = None,
    model_year: int | None = None,
    distance_activity: str | None = None,
    data_quality_tier: int = 4,
) -> CombustionResult:
    """Compute gas masses for one mobile-combustion activity record.

    Args:
        fuel_or_activity: fuel-based CO2 key (motor_gasoline, diesel, cng, ...).
        fuel_quantity/unit: gallons (liquids) or scf (CNG) — must match the EF basis.
        miles/model_year/distance_activity: on-road CH4/N2O inputs. When omitted,
            only CO2 is computed (fuel-only record; CH4/N2O flagged as a data gap).
        data_quality_tier: 1..5 evidence tier.
    """
    co2_ef = library.select(fuel_or_activity, "mobile_combustion", "CO2")
    _check_fuel_unit(fuel_unit, co2_ef.unit)

    kg_co2 = fuel_quantity * co2_ef.value
    masses = GasMasses()
    if co2_ef.biogenic:
        masses.kg_co2_biogenic = kg_co2
    else:
        masses.kg_co2_fossil = kg_co2

    ef_refs = [_ref(co2_ef)]
    if miles is not None and model_year is not None and distance_activity is not None:
        ch4_ef = library.select(distance_activity, "mobile_onroad", "CH4", model_year=model_year)
        n2o_ef = library.select(distance_activity, "mobile_onroad", "N2O", model_year=model_year)
        masses.kg_ch4 = miles * ch4_ef.value * G_PER_MILE_TO_KG
        masses.kg_n2o = miles * n2o_ef.value * G_PER_MILE_TO_KG
        ef_refs += [_ref(ch4_ef), _ref(n2o_ef)]

    return CombustionResult(
        source_category="mobile_combustion",
        gas_masses=masses,
        biogenic_fossil_tag="biogenic" if co2_ef.biogenic else "fossil",
        data_quality_tier=data_quality_tier,
        calculation_method="distance_based" if miles is not None else "EF_Tier1",
        activity_value=fuel_quantity,
        activity_unit=fuel_unit,
        ef_refs=ef_refs,
    )


def _check_fuel_unit(fuel_unit: str, ef_unit: str) -> None:
    """Ensure the activity unit matches the EF denominator (gal vs scf)."""
    ef_basis = ef_unit.split("/")[-1].strip().lower()   # 'gal' or 'scf'
    u = fuel_unit.strip().lower()
    aliases = {"gallons": "gal", "gal": "gal", "scf": "scf"}
    if aliases.get(u, u) != ef_basis:
        raise ValueError(
            f"Fuel unit {fuel_unit!r} does not match EF basis {ef_unit!r}."
        )


def _ref(ef) -> EmissionFactorRef:
    return EmissionFactorRef(
        gas=ef.gas, value=ef.value, unit=ef.unit,
        source=ef.source, source_version=ef.source_version,
        selection_rank=ef.selection_rank,
    )
