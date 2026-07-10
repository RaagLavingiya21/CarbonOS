"""Platform-agnostic scoring for Scope 2 OCR extraction.

Pure functions comparing an extraction (BillExtraction + its normalized meter rows)
against a ground-truth label. Deliberately decoupled from any eval platform: the
same functions score the deterministic golden tier (recorded model output, run in
CI) and the live tier (real Claude vision on redacted bills). The live runner can
emit a local JSON scorecard or push these numbers to LangSmith — no rework either
way.

Four metric families (emit all; weight them later once real numbers exist):
  1. field_accuracy      — fraction of header+meter fields matching the label.
  2. mwh                  — end-to-end: normalized MWh within tolerance (what the
                           calc engine actually consumes), plus total MWh error.
  3. review              — meter-level precision/recall of the needs_review flag
                           against whether the meter actually had a wrong field.
                           This is what calibrates REVIEW_THRESHOLD empirically.
  4. cost_latency        — populated only by the live tier (USD + seconds/doc).

Meter matching: extracted rows and label meters are aligned after sorting both by
(carrier, period_start); a count mismatch is itself penalized as missing/extra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from s2_ingestion.ocr import BillExtraction, ExtractedMeterRow

_REL_TOL = 0.01  # 1% relative tolerance for consumption / cost / MWh


# --- comparison helpers ----------------------------------------------------


def _norm(s: object) -> str:
    return str(s).strip().lower() if s is not None else ""


def _num_close(a: float | None, b: float | None, rel: float = _REL_TOL) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if b == 0:
        return abs(a) <= rel
    return abs(a - b) / abs(b) <= rel


def _iso(d: date | None) -> str:
    return d.isoformat() if d else ""


# --- per-meter field comparison --------------------------------------------

# (field name, is-critical) — critical fields drive the review metric's "wrong".
_METER_COMPARISONS = (
    "energy_carrier",
    "service_period_start",
    "service_period_end",
    "consumption_quantity",
    "consumption_unit",
    "is_estimated_read",
)


def _meter_field_hits(row: ExtractedMeterRow, label: dict) -> dict[str, bool]:
    """Per-field correctness of one matched meter row vs. its label."""
    return {
        "energy_carrier": _norm(row.energy_carrier) == _norm(label.get("energy_carrier")),
        "service_period_start": _iso(row.period_start) == str(label.get("service_period_start", "")),
        "service_period_end": _iso(row.period_end) == str(label.get("service_period_end", "")),
        "consumption_quantity": _num_close(row.raw_quantity, label.get("consumption_quantity")),
        "consumption_unit": _norm(row.raw_unit) == _norm(label.get("consumption_unit")),
        "is_estimated_read": bool(row.is_estimated_read) == bool(label.get("is_estimated_read", False)),
    }


def _sort_key_row(row: ExtractedMeterRow) -> tuple:
    return (_norm(row.energy_carrier), _iso(row.period_start))


def _sort_key_label(label: dict) -> tuple:
    return (_norm(label.get("energy_carrier")), str(label.get("service_period_start", "")))


# --- scorecard -------------------------------------------------------------


@dataclass
class CaseScore:
    case: str
    field_accuracy: float
    fields_total: int
    fields_correct: int
    mwh_within_tol: int
    mwh_meters: int
    total_mwh_abs_error: float
    # review flag vs. actual wrongness, at meter granularity
    review_tp: int = 0
    review_fp: int = 0
    review_fn: int = 0
    meter_count_mismatch: int = 0
    # A submitted bill that the model returned *no* meters for. Invisible to the
    # per-meter review metric (no rows to flag), so tracked explicitly — otherwise
    # a total extraction failure silently inflates the MWh coverage rate.
    extraction_empty: bool = False
    cost_usd: float | None = None
    latency_s: float | None = None

    @property
    def review_precision(self) -> float:
        flagged = self.review_tp + self.review_fp
        return self.review_tp / flagged if flagged else 1.0

    @property
    def review_recall(self) -> float:
        wrong = self.review_tp + self.review_fn
        return self.review_tp / wrong if wrong else 1.0

    def to_dict(self) -> dict:
        return {
            "case": self.case,
            "field_accuracy": round(self.field_accuracy, 4),
            "fields_correct": self.fields_correct,
            "fields_total": self.fields_total,
            "mwh_within_tol": self.mwh_within_tol,
            "mwh_meters": self.mwh_meters,
            "total_mwh_abs_error": round(self.total_mwh_abs_error, 6),
            "review_precision": round(self.review_precision, 4),
            "review_recall": round(self.review_recall, 4),
            "meter_count_mismatch": self.meter_count_mismatch,
            "extraction_empty": self.extraction_empty,
            "cost_usd": self.cost_usd,
            "latency_s": self.latency_s,
        }


def score_case(
    case: str,
    extraction: BillExtraction,
    rows: list[ExtractedMeterRow],
    label: dict,
    *,
    cost_usd: float | None = None,
    latency_s: float | None = None,
) -> CaseScore:
    """Score one extraction against its label across all four metric families."""
    fields_correct = 0
    fields_total = 0

    # Header fields.
    for name in ("utility_name", "account_number", "service_address"):
        expected = label.get("header", {}).get(name)
        if expected is None:
            continue
        got = extraction.header.get(name)
        fields_total += 1
        if got is not None and _norm(got.value) == _norm(expected):
            fields_correct += 1

    # Align meters.
    got_rows = sorted(rows, key=_sort_key_row)
    label_meters = sorted(label.get("meters", []), key=_sort_key_label)
    meter_count_mismatch = abs(len(got_rows) - len(label_meters))
    # A submitted bill expected to have meters but from which none were extracted.
    extraction_empty = bool(label_meters) and not got_rows

    mwh_within = 0
    mwh_meters = 0
    total_mwh_err = 0.0
    review_tp = review_fp = review_fn = 0

    for row, lbl in zip(got_rows, label_meters):
        hits = _meter_field_hits(row, lbl)
        fields_total += len(hits)
        fields_correct += sum(hits.values())

        # End-to-end MWh.
        mwh_meters += 1
        if _num_close(row.canonical_mwh, lbl.get("canonical_mwh")):
            mwh_within += 1
        if row.canonical_mwh is not None and lbl.get("canonical_mwh") is not None:
            total_mwh_err += abs(row.canonical_mwh - lbl["canonical_mwh"])

        # Review flag vs. actual wrongness (any compared field wrong = wrong meter).
        meter_wrong = not all(hits.values())
        if row.needs_review and meter_wrong:
            review_tp += 1
        elif row.needs_review and not meter_wrong:
            review_fp += 1
        elif not row.needs_review and meter_wrong:
            review_fn += 1

    field_accuracy = fields_correct / fields_total if fields_total else 0.0
    return CaseScore(
        case=case,
        field_accuracy=field_accuracy,
        fields_total=fields_total,
        fields_correct=fields_correct,
        mwh_within_tol=mwh_within,
        mwh_meters=mwh_meters,
        total_mwh_abs_error=total_mwh_err,
        review_tp=review_tp,
        review_fp=review_fp,
        review_fn=review_fn,
        meter_count_mismatch=meter_count_mismatch,
        extraction_empty=extraction_empty,
        cost_usd=cost_usd,
        latency_s=latency_s,
    )


@dataclass
class Scorecard:
    """Aggregate across cases — the top-line the runner prints / logs."""

    cases: list[CaseScore] = field(default_factory=list)

    def add(self, score: CaseScore) -> None:
        self.cases.append(score)

    @property
    def field_accuracy(self) -> float:
        tot = sum(c.fields_total for c in self.cases)
        cor = sum(c.fields_correct for c in self.cases)
        return cor / tot if tot else 0.0

    @property
    def mwh_within_tol_rate(self) -> float:
        tot = sum(c.mwh_meters for c in self.cases)
        hit = sum(c.mwh_within_tol for c in self.cases)
        return hit / tot if tot else 0.0

    @property
    def review_precision(self) -> float:
        tp = sum(c.review_tp for c in self.cases)
        fp = sum(c.review_fp for c in self.cases)
        return tp / (tp + fp) if (tp + fp) else 1.0

    @property
    def review_recall(self) -> float:
        tp = sum(c.review_tp for c in self.cases)
        fn = sum(c.review_fn for c in self.cases)
        return tp / (tp + fn) if (tp + fn) else 1.0

    @property
    def extraction_failure_rate(self) -> float:
        """Fraction of bills that yielded no meters — a total extraction failure
        that the MWh coverage rate would otherwise hide (those bills are absent
        from the per-meter averages entirely)."""
        return sum(c.extraction_empty for c in self.cases) / len(self.cases) if self.cases else 0.0

    def summary(self) -> dict:
        return {
            "n_cases": len(self.cases),
            "field_accuracy": round(self.field_accuracy, 4),
            "mwh_within_tol_rate": round(self.mwh_within_tol_rate, 4),
            "review_precision": round(self.review_precision, 4),
            "review_recall": round(self.review_recall, 4),
            "extraction_failure_rate": round(self.extraction_failure_rate, 4),
            "cases": [c.to_dict() for c in self.cases],
        }


__all__ = ["CaseScore", "Scorecard", "score_case"]
