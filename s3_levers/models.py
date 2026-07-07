"""Dataclasses for Epic I — reduction levers, MAC, and green-claims. DB-free."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Lever:
    lever_id: str
    name: str
    category: int  # target Scope 3 category
    abatement_pct: float  # ROUGH fraction of that category's emissions
    cost_per_tco2e: float  # ROUGH $/tCO2e (negative = net saving)
    applicability: list[str]
    source: str


@dataclass
class MACPoint:
    lever_id: str
    name: str
    category: int
    abatement_tco2e: float
    cost_per_tco2e: float
    cumulative_abatement_tco2e: float


@dataclass
class ComplianceFlag:
    rule_id: str
    jurisdiction: str
    framework: str
    verdict: str  # prohibited | watch
    note: str


@dataclass
class ClaimAssessment:
    claim_text: str
    jurisdiction: str
    substantiable: bool
    substantiation_reason: str
    ruleset_version: str
    flags: list[ComplianceFlag] = field(default_factory=list)
