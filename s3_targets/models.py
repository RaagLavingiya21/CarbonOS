"""Dataclasses for the Scope-3 SBTi/FLAG target wizard (Epic D).

DB-free. The API/persistence layer (Epic D DB phases) maps these onto the
`targets` tables; the math here is pure and unit-testable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from s3_obligations.sbti_readiness import SBTiReadiness


@dataclass
class TrajectoryPoint:
    year: int
    target_kg_co2e: float


@dataclass
class TargetTrajectory:
    method: str  # "absolute" | "intensity"
    base_year: int
    target_year: int
    base_kg_co2e: float
    reduction_pct: float  # fraction, e.g. 0.42
    points: list[TrajectoryPoint] = field(default_factory=list)

    @property
    def target_kg_co2e(self) -> float:
        return self.points[-1].target_kg_co2e if self.points else self.base_kg_co2e


@dataclass
class AmbitionCheck:
    chosen_reduction_pct: float
    reference_reduction_pct: float  # SBTi ACA reference (labeled, verify)
    meets_reference: bool
    note: str


@dataclass
class FlagAssessment:
    is_flag_required: bool
    flag_share: float  # fraction of total emissions from FLAG
    reason: str
    no_deforestation_commitment_date: str | None = None


@dataclass
class DraftTarget:
    """The wizard output: coverage readiness + trajectory + ambition + FLAG."""

    version: str  # "v2.0" | "v1.3.1"
    horizon: str  # "near_term" | "net_zero"
    readiness: SBTiReadiness
    trajectory: TargetTrajectory
    ambition: AmbitionCheck
    flag: FlagAssessment | None = None
    notes: list[str] = field(default_factory=list)
