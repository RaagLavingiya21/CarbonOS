"""Deterministic eval for the Epic B questionnaire framework detector (P.4.2.1).

Asserts, over a labeled fixture:
  - detection accuracy on the confident cases,
  - the SAFETY property (never confidently mis-label): on ambiguous cases the
    detector returns `generic` or flags low-confidence — never a confident wrong
    framework,
  - question parsing produces typed questions,
  - determinism.

No API key / network. Run standalone for a report:
    python -m evals.test_framework_detection
Or under pytest.
"""

from __future__ import annotations

import json
from pathlib import Path

from s3_questionnaire.framework_detector import detect_framework, parse_questionnaire

_FIXTURE = Path(__file__).parent / "fixtures" / "framework_detection_cases.json"
_CONFIDENT_ACCURACY_FLOOR = 1.0  # all confident cases must be correctly labeled


def _cases() -> list[dict]:
    return json.loads(_FIXTURE.read_text())["cases"]


def test_confident_cases_detected_correctly():
    confident = [c for c in _cases() if c.get("confident")]
    hits = sum(
        1 for c in confident if detect_framework(c["text"]).framework == c["expected_framework"]
    )
    acc = hits / len(confident)
    assert acc >= _CONFIDENT_ACCURACY_FLOOR, f"confident detection accuracy {acc:.0%}"


def test_never_confidently_mislabels():
    """The trust invariant: an ambiguous questionnaire must be `generic` OR
    flagged low-confidence — never a confident specific framework."""
    offenders = []
    for c in _cases():
        if c.get("confident"):
            continue
        d = detect_framework(c["text"])
        confident_specific = d.framework != "generic" and not d.is_low_confidence
        if confident_specific:
            offenders.append(f"{c['name']} -> {d.framework} @ {d.confidence}")
    assert not offenders, f"confident mislabels on ambiguous input: {offenders}"


def test_ambiguous_cases_resolve_generic():
    for c in _cases():
        if c.get("confident"):
            continue
        d = detect_framework(c["text"])
        assert d.framework == c["expected_framework"] or d.is_low_confidence


def test_questions_parsed_with_types():
    for c in _cases():
        if not c.get("confident"):
            continue
        pq = parse_questionnaire(c["text"])
        assert pq.questions, f"{c['name']} parsed no questions"
        for want in c.get("expect_types", []):
            assert any(q.question_type == want for q in pq.questions), (
                f"{c['name']} missing a {want} question"
            )


def test_cdp_field_keys_extracted():
    cdp = next(c for c in _cases() if c["name"] == "cdp_climate")
    pq = parse_questionnaire(cdp["text"])
    keys = [q.framework_field_key for q in pq.questions if q.framework_field_key]
    assert any(k and k.startswith("cdp.C6") for k in keys)


def test_determinism():
    for c in _cases():
        a = detect_framework(c["text"])
        b = detect_framework(c["text"])
        assert (a.framework, a.confidence, a.is_low_confidence) == (
            b.framework,
            b.confidence,
            b.is_low_confidence,
        )


def _report() -> None:
    print("\nFramework detection eval\n")
    for c in _cases():
        d = detect_framework(c["text"])
        pq = parse_questionnaire(c["text"])
        exp = c["expected_framework"]
        ok = "OK " if d.framework == exp else "MISS"
        flag = " (low-conf)" if d.is_low_confidence else ""
        print(
            f"  [{ok}] {c['name']:<38} -> {d.framework:<10} @ {d.confidence:>5}{flag}"
            f"  | {len(pq.questions)} questions"
        )


if __name__ == "__main__":
    _report()
