"""Deterministic golden evals for Scope 2 OCR (CI, no LLM call).

Replays recorded model outputs through the real parse+normalize+scoring path and
asserts the metric behavior we rely on. This regression-guards the extractor logic
(and the scorer) independently of any live model. Real-doc/live evals run manually
via run_live.py and are not collected here.
"""

from __future__ import annotations

from evals.scope2_ocr.harness import run_golden_case, run_golden_scorecard


def test_clean_bill_scores_perfect_and_flags_nothing() -> None:
    score = run_golden_case("single_elec")
    assert score.field_accuracy == 1.0
    assert score.mwh_within_tol == score.mwh_meters == 1
    assert (score.review_tp, score.review_fp, score.review_fn) == (0, 0, 0)
    assert score.meter_count_mismatch == 0


def test_multimeter_flags_the_wrong_gas_read() -> None:
    score = run_golden_case("multimeter_elec_gas")
    # Two meters extracted; only the electricity meter is within MWh tolerance.
    assert score.mwh_meters == 2
    assert score.mwh_within_tol == 1
    # The mis-read gas field drops field accuracy below perfect...
    assert score.field_accuracy < 1.0
    # ...and the low-confidence flag *caught* it (no wrong meter slipped through).
    assert score.review_fn == 0
    assert score.review_recall == 1.0
    assert score.review_tp == 1


def test_low_confidence_correct_read_is_routed_to_review() -> None:
    """A correct read with sub-threshold confidence must still flag for review.

    Guards the REVIEW_THRESHOLD path directly: nothing is wrong (field_accuracy
    1.0, no false negative), yet the low quantity confidence routes the meter to
    review — a deliberate false-positive we accept to never miss a real misread.
    """
    score = run_golden_case("degraded_lowconf_elec")
    assert score.field_accuracy == 1.0
    assert score.mwh_within_tol == score.mwh_meters == 1
    assert (score.review_tp, score.review_fp, score.review_fn) == (0, 1, 0)
    assert score.review_recall == 1.0  # no wrong meter slipped through


def test_empty_extraction_is_counted_not_hidden() -> None:
    """A bill the model returned no meters for is a total failure the per-meter
    review metric can't see — it must be flagged explicitly (extraction_empty)."""
    score = run_golden_case("empty_extraction")
    assert score.extraction_empty is True
    assert score.mwh_meters == 0  # nothing extracted...
    assert score.meter_count_mismatch == 1  # ...but the label expected a meter


def test_scorecard_never_silently_passes_a_wrong_meter() -> None:
    """Aggregate invariant: review recall is 1.0 across the golden set."""
    card = run_golden_scorecard()
    summary = card.summary()
    assert summary["n_cases"] == 4
    assert card.review_recall == 1.0
    assert card.field_accuracy > 0.9
    # One of the four golden bills is a total extraction failure — surfaced, not hidden.
    assert summary["extraction_failure_rate"] == 0.25
