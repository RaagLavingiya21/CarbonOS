"""Stationary combustion calc (Tier 1/2).

    CO2_kg = heat_input_mmBtu × EF_CO2
    CH4_kg = heat_input_mmBtu × EF_CH4
    N2O_kg = heat_input_mmBtu × EF_N2O

All EPA EFs are HHV-basis. Outputs gas masses only. See research/2.1 section 1.
"""

from __future__ import annotations

from s1_calc.models import CombustionResult, EmissionFactorRef, GasMasses
from s1_calc.units import to_mmbtu
from s1_factors.library import EmissionFactorLibrary


def calculate_stationary(
    fuel_or_activity: str,
    activity_value: float,
    activity_unit: str,
    library: EmissionFactorLibrary,
    *,
    biogenic: bool = False,
    hhv_override: float | None = None,
    data_quality_tier: int = 4,
) -> CombustionResult:
    """Compute gas masses for one stationary-combustion activity record.

    Args:
        fuel_or_activity: e.g. natural_gas, diesel_no2.
        activity_value/unit: fuel consumed (therms|mmBtu|GJ|scf|Ccf|Mcf|gal|ton).
        biogenic: True routes CO2 to the biogenic bucket (excluded from S1 total).
        hhv_override: measured HHV (mmBtu per native unit) -> Tier 2; else default.
        data_quality_tier: 1..5 evidence tier, assigned by the intake layer.
    """
    co2_ef = library.select(fuel_or_activity, "stationary_combustion", "CO2")
    ch4_ef = library.select(fuel_or_activity, "stationary_combustion", "CH4")
    n2o_ef = library.select(fuel_or_activity, "stationary_combustion", "N2O")

    hhv = hhv_override if hhv_override is not None else co2_ef.hhv
    heat_input = to_mmbtu(activity_value, activity_unit, hhv)

    kg_co2 = heat_input * co2_ef.value
    masses = GasMasses(
        kg_ch4=heat_input * ch4_ef.value,
        kg_n2o=heat_input * n2o_ef.value,
    )
    if biogenic:
        masses.kg_co2_biogenic = kg_co2
    else:
        masses.kg_co2_fossil = kg_co2

    return CombustionResult(
        source_category="stationary_combustion",
        gas_masses=masses,
        biogenic_fossil_tag="biogenic" if biogenic else "fossil",
        data_quality_tier=data_quality_tier,
        calculation_method="EF_Tier2" if hhv_override is not None else "EF_Tier1",
        activity_value=activity_value,
        activity_unit=activity_unit,
        heat_input_mmbtu=heat_input,
        ef_refs=[_ref(ef) for ef in (co2_ef, ch4_ef, n2o_ef)],
    )


def _ref(ef) -> EmissionFactorRef:
    return EmissionFactorRef(
        gas=ef.gas, value=ef.value, unit=ef.unit,
        source=ef.source, source_version=ef.source_version,
        selection_rank=ef.selection_rank,
    )
