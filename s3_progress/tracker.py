"""Progress vs target trajectory (Epic E / E2) + base-year recalc policy (E3).

Only REAL reductions count toward on/off-track — the like-for-like current total
(base + real delta) is compared to the Epic D trajectory; method-driven change is
reported separately as a caveat. Base-year recalculation follows the GHG Protocol
significance-threshold rule. Pure logic, DB-free.
"""

from __future__ import annotations

from s3_progress.models import Decomposition, ProgressResult, RecalcDecision

# GHG Protocol base-year recalculation significance threshold (configurable).
_DEFAULT_SIGNIFICANCE_THRESHOLD = 0.05  # 5% of base-year emissions
_STRUCTURAL_TRIGGERS = {"ma", "divestment", "structural", "methodology", "error_correction"}


def track_progress(
    decomposition: Decomposition,
    base_total_kg: float,
    trajectory: dict[int, float],
) -> ProgressResult:
    """Compare the like-for-like current total to the target trajectory."""
    real_total = base_total_kg + decomposition.real_delta  # real change only
    actual_total = base_total_kg + decomposition.total_delta
    target = trajectory.get(decomposition.current_year)

    on_track: bool | None = None if target is None else real_total <= target + 1e-9

    notes: list[str] = []
    if abs(decomposition.method_delta) > 0:
        notes.append(
            f"{decomposition.method_delta:+.0f} kg of the change is method/data-driven "
            "(EF version, method switch, or completeness) and does NOT count as a real reduction."
        )
    if target is None:
        notes.append(
            f"No trajectory target for {decomposition.current_year} — status undetermined."
        )

    return ProgressResult(
        current_year=decomposition.current_year,
        base_total_kg=base_total_kg,
        real_total_kg=real_total,
        actual_total_kg=actual_total,
        trajectory_target_kg=target,
        on_track=on_track,
        method_delta_kg=decomposition.method_delta,
        notes=notes,
    )


def evaluate_recalc(
    trigger: str,
    significance_pct: float,
    *,
    threshold_pct: float = _DEFAULT_SIGNIFICANCE_THRESHOLD,
) -> RecalcDecision:
    """Decide whether the base year must be recalculated.

    Per GHG Protocol, structural changes (M&A, divestments, methodology changes,
    error corrections) that exceed a significance threshold require recalculating
    the base year so comparisons stay like-for-like. Organic growth/reductions do
    NOT trigger a recalc.
    """
    is_structural = trigger in _STRUCTURAL_TRIGGERS
    required = is_structural and significance_pct >= threshold_pct

    if not is_structural:
        rationale = (
            f"Trigger '{trigger}' is not a structural change — no base-year recalc "
            "(organic change is tracked as progress, not restated)."
        )
    elif required:
        rationale = (
            f"Structural change '{trigger}' at {significance_pct:.0%} of base-year emissions "
            f"exceeds the {threshold_pct:.0%} threshold — recalculate the (single, physical) "
            "base year."
        )
    else:
        rationale = (
            f"Structural change '{trigger}' at {significance_pct:.0%} is below the "
            f"{threshold_pct:.0%} threshold — no recalc required."
        )

    return RecalcDecision(
        trigger=trigger,
        significance_pct=significance_pct,
        threshold_pct=threshold_pct,
        recalc_required=required,
        rationale=rationale,
    )
