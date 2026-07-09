"""Calibrate REVIEW_THRESHOLD from scored OCR runs.

`s2_ingestion/ocr.py` routes a meter to human review when its minimum critical-field
confidence drops below REVIEW_THRESHOLD (or a parse/normalize reason fires). That
threshold was a hardcoded guess (0.85). This module turns a corpus of scored
extractions into a data-driven recommendation.

Pure functions over `Observation`s — one per extracted meter, capturing its
confidence, whether it was actually wrong, and whether a non-confidence reason
already forces review. `sweep_threshold` computes review precision/recall at each
candidate cutoff (mirroring the TP/FP/FN definitions in `scoring.py`), and
`recommend_threshold` picks a cutoff that catches enough real misreads.

Objective: a false negative (a wrong meter that is NOT flagged) silently corrupts
the emissions inventory, which we weight as worse than a false positive (an extra
human review). So the default rule is: **meet a recall floor, then maximize
precision** — i.e. the smallest cutoff that still catches `min_recall` of misreads.
"""

from __future__ import annotations

from dataclasses import dataclass

from evals.scope2_ocr.scoring import _meter_field_hits, _sort_key_label, _sort_key_row
from s2_ingestion.ocr import ExtractedMeterRow


@dataclass(frozen=True)
class Observation:
    """One extracted meter's calibration signal.

    - min_confidence:   the row's min critical-field confidence (drives the cutoff).
    - meter_wrong:      any compared field disagreed with the label.
    - has_review_reason: a parse/normalize reason already forces review regardless
                         of the confidence cutoff (mirrors `needs_review`).
    """

    min_confidence: float
    meter_wrong: bool
    has_review_reason: bool = False

    def flagged_at(self, threshold: float) -> bool:
        return self.has_review_reason or self.min_confidence < threshold


@dataclass(frozen=True)
class ThresholdPoint:
    threshold: float
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int

    def to_dict(self) -> dict:
        return {
            "threshold": round(self.threshold, 4),
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1": round(self.f1, 4),
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
        }


def default_grid() -> list[float]:
    """Candidate cutoffs from 0.50 to 0.99 inclusive, step 0.01."""
    return [round(0.50 + 0.01 * i, 2) for i in range(50)]


def _point(observations: list[Observation], threshold: float) -> ThresholdPoint:
    tp = fp = fn = 0
    for obs in observations:
        flagged = obs.flagged_at(threshold)
        if flagged and obs.meter_wrong:
            tp += 1
        elif flagged and not obs.meter_wrong:
            fp += 1
        elif not flagged and obs.meter_wrong:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return ThresholdPoint(threshold, precision, recall, f1, tp, fp, fn)


def sweep_threshold(
    observations: list[Observation],
    grid: list[float] | None = None,
) -> list[ThresholdPoint]:
    """Review precision/recall/F1 at each candidate cutoff over the corpus."""
    return [_point(observations, t) for t in (grid if grid is not None else default_grid())]


def recommend_threshold(
    observations: list[Observation],
    *,
    min_recall: float = 0.95,
    grid: list[float] | None = None,
) -> float:
    """Smallest cutoff meeting `min_recall`, breaking ties toward higher precision.

    Rationale: recall (catching misreads) is monotone non-decreasing in the cutoff
    while precision trends down, so the smallest recall-satisfying cutoff maximizes
    precision. If no cutoff reaches `min_recall`, return the highest-recall cutoff
    (best effort), tie-broken by precision.
    """
    points = sweep_threshold(observations, grid)
    qualifying = [p for p in points if p.recall >= min_recall]
    if qualifying:
        # Smallest threshold among those meeting the recall floor.
        best = min(qualifying, key=lambda p: (p.threshold, -p.precision))
        return best.threshold
    # Nothing meets the floor: fall back to the best achievable recall.
    best = max(points, key=lambda p: (p.recall, p.precision))
    return best.threshold


def observations_from_rows(rows: list[ExtractedMeterRow], label: dict) -> list[Observation]:
    """Build per-meter `Observation`s from a scored extraction, aligned as in scoring.

    Alignment mirrors `score_case`: sort both sides by (carrier, period_start) and
    zip. Unmatched rows/meters are dropped from calibration (count mismatch is a
    separate metric already tracked by the scorecard).
    """
    got_rows = sorted(rows, key=_sort_key_row)
    label_meters = sorted(label.get("meters", []), key=_sort_key_label)
    observations: list[Observation] = []
    for row, lbl in zip(got_rows, label_meters):
        hits = _meter_field_hits(row, lbl)
        observations.append(
            Observation(
                min_confidence=row.min_confidence,
                meter_wrong=not all(hits.values()),
                has_review_reason=bool(row.review_reasons),
            )
        )
    return observations


__all__ = [
    "Observation",
    "ThresholdPoint",
    "default_grid",
    "sweep_threshold",
    "recommend_threshold",
    "observations_from_rows",
]
