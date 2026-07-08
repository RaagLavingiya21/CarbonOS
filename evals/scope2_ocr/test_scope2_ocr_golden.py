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


def test_scorecard_never_silently_passes_a_wrong_meter() -> None:
    """Aggregate invariant: review recall is 1.0 across the golden set."""
    card = run_golden_scorecard()
    assert card.summary()["n_cases"] == 2
    assert card.review_recall == 1.0
    assert card.field_accuracy > 0.9
