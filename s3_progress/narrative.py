"""Deterministic progress narrative (Epic E / E4, unit P.4.4.b).

Builds a grounded progress statement from the decomposition + progress result.
No LLM: every figure comes from the computed deltas, so the narrative claims
ONLY real reductions and never fabricates a number.
"""

from __future__ import annotations

from s3_progress.models import Decomposition, ProgressResult


def build_progress_narrative(decomposition: Decomposition, progress: ProgressResult) -> str:
    real = decomposition.real_delta
    direction = "reduced" if real < 0 else "increased" if real > 0 else "held flat on"
    pct = abs(real) / progress.base_total_kg if progress.base_total_kg else 0.0

    lines = [
        f"Between {decomposition.base_year} and {progress.current_year}, real (like-for-like) "
        f"Scope 3 emissions {direction} by {abs(real):.0f} kg CO2e ({pct:.1%} of the base year).",
    ]
    if progress.trajectory_target_kg is not None:
        status = "on track" if progress.on_track else "off track"
        lines.append(
            f"Against the target trajectory ({progress.trajectory_target_kg:.0f} kg for "
            f"{progress.current_year}), the like-for-like total of {progress.real_total_kg:.0f} kg "
            f"is {status}."
        )
    if abs(progress.method_delta_kg) > 0:
        lines.append(
            f"Note: {progress.method_delta_kg:+.0f} kg of the reported change is "
            "method/data-driven (emission-factor version, method switch, or completeness) "
            "and is excluded from the real-reduction claim."
        )
    return " ".join(lines)
