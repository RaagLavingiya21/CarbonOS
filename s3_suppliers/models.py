"""Dataclasses for Epic F — supplier engagement at program scale. DB-free.

Note: the actual outreach loop (draft email → parse response → route) is the
shared `copilot` module and is out of this module's isolated scope. Epic F here
covers the pure-logic parts: cohorting suppliers by contribution and computing
program/supplier scorecards.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Supplier:
    supplier_id: str
    name: str
    scope3_category: int  # which category this supplier's spend/emissions sits in
    emissions_kg: float = 0.0
    spend_usd: float = 0.0
    pcf_received: bool = False  # has the supplier provided a primary PCF?
    dq_score: float | None = None  # data-quality score of that PCF (0–100)
    supplier_sbt_status: str = "none"  # none | committed | validated


@dataclass
class SupplierCohort:
    basis: str  # emissions | spend
    hotspot_categories: list[int]
    members: list[Supplier] = field(default_factory=list)
    emissions_covered_pct: float = 0.0  # of the hotspot categories' total emissions


@dataclass
class ProgramScorecard:
    supplier_count: int
    pcf_coverage_pct: float  # suppliers with a PCF / total
    emissions_covered_pct: float  # emissions of PCF suppliers / total emissions
    avg_dq: float | None  # mean DQ of received PCFs
    sbt_committed_count: int
    sbt_validated_count: int
