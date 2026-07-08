"""Inventory report rollup + calculation trace.

Total Scope 1 = Sigma(CO2_fossil + CH4 + N2O + SF6 + NF3) x GWP x consolidation
multiplier. Biogenic CO2 is tracked separately and never netted into the total
(GHG Protocol Ch.4). See research/2.2 section F and 2.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from s1_calc.gwp import gwp_100
from s1_calc.models import GasMasses


@dataclass
class ReportRecord:
    """A stored emission record projected for reporting."""

    record_id: str
    gas_masses: GasMasses
    multiplier: float = 1.0            # entity consolidation multiplier [0.0-1.0]
    facility_id: str | None = None
    facility_name: str | None = None
    source_id: str | None = None
    source_name: str | None = None
    fuel: str | None = None           # fuel_or_activity (GHGRP per-fuel grouping)
    ef_tier: str | None = None        # calculation tier, e.g. "T1"/"T2" (GHGRP)


@dataclass
class GasBreakdown:
    co2_fossil_tco2e: float = 0.0
    ch4_tco2e: float = 0.0
    n2o_tco2e: float = 0.0
    sf6_tco2e: float = 0.0
    nf3_tco2e: float = 0.0

    @property
    def total_tco2e(self) -> float:
        return (
            self.co2_fossil_tco2e + self.ch4_tco2e + self.n2o_tco2e
            + self.sf6_tco2e + self.nf3_tco2e
        )


@dataclass
class FacilityBreakdown:
    facility_id: str | None
    facility_name: str | None
    tco2e: float


@dataclass
class InventoryReport:
    ar_version: str
    total_scope1_tco2e: float
    biogenic_co2_tco2e: float          # separate memo line, excluded from total
    by_gas: GasBreakdown
    by_facility: list[FacilityBreakdown] = field(default_factory=list)
    record_count: int = 0


@dataclass
class SourceLine:
    """A single non-combustion emission line for disclosure tables."""

    label: str
    gas_or_refrigerant: str
    facility_id: str | None
    facility_name: str | None
    tco2e: float


@dataclass
class DisclosureData:
    """Everything a disclosure needs, composing the combustion rollup with the
    fugitive + process categories so gross Scope 1 covers all three. The
    combustion `InventoryReport` is left unchanged (stays combustion-only); its
    total is never mutated. `report_records` carries the raw combustion records
    so per-gas mass / per-fuel exports (GHGRP) don't need a second DB pass."""

    combustion: InventoryReport
    fugitive_tco2e: float = 0.0
    process_tco2e: float = 0.0
    fugitive_lines: list[SourceLine] = field(default_factory=list)
    process_lines: list[SourceLine] = field(default_factory=list)
    report_records: list[ReportRecord] = field(default_factory=list)

    @property
    def ar_version(self) -> str:
        return self.combustion.ar_version

    @property
    def combustion_tco2e(self) -> float:
        return self.combustion.total_scope1_tco2e

    @property
    def gross_scope1_tco2e(self) -> float:
        """Gross Scope 1 = combustion + fugitive + process (all direct emissions)."""
        return self.combustion.total_scope1_tco2e + self.fugitive_tco2e + self.process_tco2e

    @property
    def biogenic_co2_tco2e(self) -> float:
        return self.combustion.biogenic_co2_tco2e   # memo line, still excluded


def _co2e_by_gas(masses: GasMasses, ar_version: str, multiplier: float) -> GasBreakdown:
    m = multiplier
    return GasBreakdown(
        co2_fossil_tco2e=masses.kg_co2_fossil * gwp_100("Carbon dioxide", ar_version) * m / 1000.0,
        ch4_tco2e=masses.kg_ch4 * gwp_100("Methane", ar_version, "fossil") * m / 1000.0,
        n2o_tco2e=masses.kg_n2o * gwp_100("Nitrous oxide", ar_version) * m / 1000.0,
        sf6_tco2e=masses.kg_sf6 * gwp_100("Sulfur hexafluoride", ar_version) * m / 1000.0,
        nf3_tco2e=masses.kg_nf3 * gwp_100("Nitrogen trifluoride", ar_version) * m / 1000.0,
    )


def build_inventory_report(records: list[ReportRecord], ar_version: str) -> InventoryReport:
    """Aggregate records into a GHG-Protocol-aligned inventory report."""
    agg = GasBreakdown()
    biogenic = 0.0
    facility_totals: dict[str | None, FacilityBreakdown] = {}

    for rec in records:
        gb = _co2e_by_gas(rec.gas_masses, ar_version, rec.multiplier)
        agg.co2_fossil_tco2e += gb.co2_fossil_tco2e
        agg.ch4_tco2e += gb.ch4_tco2e
        agg.n2o_tco2e += gb.n2o_tco2e
        agg.sf6_tco2e += gb.sf6_tco2e
        agg.nf3_tco2e += gb.nf3_tco2e
        biogenic += (
            rec.gas_masses.kg_co2_biogenic
            * gwp_100("Carbon dioxide", ar_version) * rec.multiplier / 1000.0
        )
        fb = facility_totals.setdefault(
            rec.facility_id,
            FacilityBreakdown(rec.facility_id, rec.facility_name, 0.0),
        )
        fb.tco2e += gb.total_tco2e

    return InventoryReport(
        ar_version=ar_version,
        total_scope1_tco2e=agg.total_tco2e,
        biogenic_co2_tco2e=biogenic,
        by_gas=agg,
        by_facility=sorted(
            facility_totals.values(), key=lambda f: f.tco2e, reverse=True
        ),
        record_count=len(records),
    )


def trace_record(record: ReportRecord, ar_version: str) -> dict:
    """The calc chain behind one record's CO2e (the 'View Source' spine).

    Returns each gas's mass -> GWP -> multiplier -> tCO2e contribution, plus the
    biogenic memo. The route layer attaches the EF provenance + evidence document.
    """
    gb = _co2e_by_gas(record.gas_masses, ar_version, record.multiplier)
    gm = record.gas_masses
    return {
        "record_id": record.record_id,
        "ar_version": ar_version,
        "consolidation_multiplier": record.multiplier,
        "gases": [
            {"gas": "CO2 (fossil)", "kg": gm.kg_co2_fossil,
             "gwp_100": gwp_100("Carbon dioxide", ar_version), "tco2e": gb.co2_fossil_tco2e},
            {"gas": "CH4", "kg": gm.kg_ch4,
             "gwp_100": gwp_100("Methane", ar_version, "fossil"), "tco2e": gb.ch4_tco2e},
            {"gas": "N2O", "kg": gm.kg_n2o,
             "gwp_100": gwp_100("Nitrous oxide", ar_version), "tco2e": gb.n2o_tco2e},
        ],
        "total_tco2e": gb.total_tco2e,
        "biogenic_co2_kg": gm.kg_co2_biogenic,
        "biogenic_co2_tco2e": (
            gm.kg_co2_biogenic * gwp_100("Carbon dioxide", ar_version) * record.multiplier / 1000.0
        ),
    }
