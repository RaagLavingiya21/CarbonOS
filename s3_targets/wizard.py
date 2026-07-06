"""SBTi target wizard math (Epic D / P.3.2). Pure, DB-free.

Composes the C4 coverage readiness (s3_obligations.sbti_readiness) with a
reduction trajectory, an ambition check, and (optionally) a FLAG assessment
into a conformant DraftTarget. Numbers are computed, never invented; the
SBTi minimum-ambition rate is a LABELED reference to verify, not asserted as
current gospel (same honesty discipline as the unconfirmed net-zero %).
"""

from __future__ import annotations

from s3_obligations.models import ObligationProfile
from s3_obligations.sbti_readiness import assess_sbti_readiness
from s3_targets.flag import assess_flag
from s3_targets.models import (
    AmbitionCheck,
    DraftTarget,
    TargetTrajectory,
    TrajectoryPoint,
)

# SBTi Absolute Contraction Approach linear rate for a 1.5°C near-term target.
# REFERENCE ONLY — verify against current SBTi criteria before relying on it.
_ACA_LINEAR_RATE_1_5C = 0.042  # ~4.2% of base-year emissions per year


def build_target_trajectory(
    base_year: int,
    base_kg_co2e: float,
    target_year: int,
    reduction_pct: float,
    method: str = "absolute",
) -> TargetTrajectory:
    """Linear reduction path from base_year to target_year.

    `reduction_pct` is a fraction in [0, 1]. For `absolute`, base_kg_co2e is a
    total; for `intensity` it is a per-unit intensity (sectoral convergence /
    SDA is not modelled here — flagged by the caller).
    """
    if target_year <= base_year:
        raise ValueError("target_year must be after base_year")
    if not 0.0 <= reduction_pct <= 1.0:
        raise ValueError("reduction_pct must be in [0, 1]")

    span = target_year - base_year
    end_value = base_kg_co2e * (1.0 - reduction_pct)
    step = (base_kg_co2e - end_value) / span
    points = [
        TrajectoryPoint(year=base_year + i, target_kg_co2e=round(base_kg_co2e - step * i, 6))
        for i in range(span + 1)
    ]
    return TargetTrajectory(
        method=method,
        base_year=base_year,
        target_year=target_year,
        base_kg_co2e=base_kg_co2e,
        reduction_pct=reduction_pct,
        points=points,
    )


def sbti_reference_reduction(base_year: int, target_year: int) -> float:
    """SBTi ACA reference cumulative reduction for the period (labeled reference)."""
    years = max(0, target_year - base_year)
    return min(_ACA_LINEAR_RATE_1_5C * years, 1.0)


def check_ambition(reduction_pct: float, base_year: int, target_year: int) -> AmbitionCheck:
    reference = sbti_reference_reduction(base_year, target_year)
    meets = reduction_pct >= reference - 1e-9
    note = (
        f"Reference: SBTi ACA ~{_ACA_LINEAR_RATE_1_5C:.1%}/yr linear (1.5°C near-term) "
        f"=> ~{reference:.0%} over {target_year - base_year} yrs. VERIFY against current "
        "SBTi criteria before relying on this rate."
    )
    return AmbitionCheck(
        chosen_reduction_pct=reduction_pct,
        reference_reduction_pct=reference,
        meets_reference=meets,
        note=note,
    )


def build_draft_target(
    profile: ObligationProfile,
    scope3_by_category: dict[int, float],
    *,
    base_year: int,
    target_year: int,
    reduction_pct: float,
    method: str = "absolute",
    covered_categories: set[int] | None = None,
    version: str = "v2.0",
    horizon: str = "near_term",
    sector: str = "",
    flag_kg_co2e: float = 0.0,
) -> DraftTarget:
    """Assemble a conformant draft SBTi target (+ FLAG if triggered)."""
    readiness = assess_sbti_readiness(
        profile,
        scope3_by_category,
        covered_categories=covered_categories,
        version=version,
        horizon=horizon,
    )
    base_total = readiness.total_scope3_kg
    trajectory = build_target_trajectory(
        base_year, base_total, target_year, reduction_pct, method=method
    )
    ambition = check_ambition(reduction_pct, base_year, target_year)

    flag = assess_flag(sector, base_total, flag_kg_co2e) if (sector or flag_kg_co2e) else None

    notes: list[str] = list(readiness.notes)
    if method == "intensity":
        notes.append(
            "Intensity method modelled as a linear path; sectoral convergence (SDA) "
            "is not computed here — confirm the method against SBTi guidance."
        )
    if not ambition.meets_reference:
        notes.append(
            f"Chosen reduction {reduction_pct:.0%} is below the SBTi ACA reference "
            f"{ambition.reference_reduction_pct:.0%} (reference — verify)."
        )

    return DraftTarget(
        version=version,
        horizon=horizon,
        readiness=readiness,
        trajectory=trajectory,
        ambition=ambition,
        flag=flag,
        notes=notes,
    )
