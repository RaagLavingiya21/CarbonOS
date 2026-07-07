"""Pure base-year recalculation logic (GHG Protocol Chapter 5).

Rules encoded here:
- **Structural changes** (acquisitions, divestitures, out/insourcing, methodology
  changes, significant error corrections) DO trigger a base-year recalculation:
  the base year is restated so it reflects the same operations/methods as the
  current inventory. Deltas are signed (add acquired operations, remove divested).
- **Organic changes** (real growth or decline — new/closed facilities, production
  changes) do NOT trigger recalculation; they're tracked for transparency only.
- A company declares a **significance threshold** (e.g. 5%). Recalculation is
  *required* once the cumulative structural change exceeds it. Below the
  threshold it's optional; if no threshold is declared we can't decide (None).

The engine is fed events (each a signed base-year delta) and reports the pending
(not-yet-applied) structural delta, the restated total, the % impact, and
whether recalculation is required under the declared policy.
"""

from __future__ import annotations

from dataclasses import dataclass

# GHG Protocol structural-change triggers → recalculate the base year.
STRUCTURAL_TRIGGERS = frozenset({
    "acquisition",
    "divestiture",
    "outsourcing",
    "insourcing",
    "methodology_change",
    "error_correction",
})
# Organic changes → real growth/decline, NEVER recalculated.
ORGANIC_TRIGGERS = frozenset({"organic_growth", "organic_decline"})
ALL_TRIGGERS = STRUCTURAL_TRIGGERS | ORGANIC_TRIGGERS


def is_structural(trigger_type: str) -> bool:
    return trigger_type in STRUCTURAL_TRIGGERS


@dataclass(frozen=True)
class RecalcEvent:
    id: str
    trigger_type: str
    description: str | None
    delta_tco2e: float          # signed base-year emissions to add(+)/remove(-)
    applied: bool = False       # already folded into the stored base-year total
    effective_date: str | None = None


@dataclass(frozen=True)
class EnrichedEvent:
    id: str
    trigger_type: str
    description: str | None
    delta_tco2e: float
    applied: bool
    effective_date: str | None
    is_structural: bool


@dataclass(frozen=True)
class RecalcAnalysis:
    base_year: int | None
    base_year_total_tco2e: float          # current (possibly already restated) total
    significance_threshold_pct: float | None
    events: list[EnrichedEvent]
    structural_delta_pending: float       # sum of not-yet-applied structural deltas
    organic_delta: float                  # informational only (excluded from recalc)
    restated_total: float                 # current total + pending structural delta
    pct_impact: float | None              # |pending structural| / current total * 100
    recalc_required: bool | None          # None = threshold not declared / undecidable
    has_pending: bool


def analyze_recalc(
    *,
    base_year: int | None,
    base_year_total_tco2e: float | None,
    significance_threshold_pct: float | None,
    events: list[RecalcEvent],
) -> RecalcAnalysis:
    current = float(base_year_total_tco2e or 0.0)

    enriched: list[EnrichedEvent] = []
    pending_structural = 0.0
    organic = 0.0
    for e in events:
        structural = is_structural(e.trigger_type)
        enriched.append(
            EnrichedEvent(
                id=e.id,
                trigger_type=e.trigger_type,
                description=e.description,
                delta_tco2e=e.delta_tco2e,
                applied=e.applied,
                effective_date=e.effective_date,
                is_structural=structural,
            )
        )
        if structural and not e.applied:
            pending_structural += e.delta_tco2e
        elif not structural:
            organic += e.delta_tco2e

    restated = current + pending_structural
    pct_impact = (abs(pending_structural) / current * 100.0) if current else None

    if significance_threshold_pct is None or pct_impact is None:
        recalc_required: bool | None = None
    else:
        recalc_required = pct_impact >= significance_threshold_pct

    return RecalcAnalysis(
        base_year=base_year,
        base_year_total_tco2e=current,
        significance_threshold_pct=significance_threshold_pct,
        events=enriched,
        structural_delta_pending=pending_structural,
        organic_delta=organic,
        restated_total=restated,
        pct_impact=pct_impact,
        recalc_required=recalc_required,
        has_pending=pending_structural != 0.0,
    )
