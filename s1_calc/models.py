"""Data model for the Scope 1 combustion calc engine.

The engine outputs GAS MASSES in kg per species — never CO2e. CO2e is a
downstream reporting transform (see s1_calc.gwp). Every result carries the EF
provenance needed for the audit "View Source" trace.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GasMasses:
    """Immutable physical record: kg per gas species. No CO2e here."""

    kg_co2_fossil: float = 0.0
    kg_co2_biogenic: float = 0.0   # separate disclosure; excluded from S1 total
    kg_ch4: float = 0.0
    kg_n2o: float = 0.0
    kg_sf6: float = 0.0
    kg_nf3: float = 0.0


@dataclass(frozen=True)
class EmissionFactorRef:
    """Provenance snapshot of an EF applied in a calculation (for View Source)."""

    gas: str
    value: float
    unit: str
    source: str
    source_version: str
    selection_rank: int


@dataclass
class CombustionResult:
    source_category: str            # stationary_combustion|mobile_combustion
    gas_masses: GasMasses
    biogenic_fossil_tag: str        # fossil|biogenic|mixed|not_applicable
    data_quality_tier: int          # 1..5
    calculation_method: str         # EF_Tier1|EF_Tier2|distance_based
    activity_value: float
    activity_unit: str
    heat_input_mmbtu: float | None = None   # auditable intermediate (stationary)
    ef_refs: list[EmissionFactorRef] = field(default_factory=list)
