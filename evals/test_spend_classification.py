"""Deterministic eval for the Epic A spend->Scope3-category classifier (P.2.2.b).

Runs the classifier over a labeled fixture and asserts:
  - overall + per-category accuracy meets a floor,
  - flagged lines (energy/no-match) are flagged,
  - the same input yields an identical classification (determinism invariant).

This is the "prototype against a labeled set before wiring the UI" step from
scope3-gap-analysis/04-epic-a-implementation-plan.md (A3). No API key / network:
it uses the local Open CEDA 2025 workbook via factors/ef_lookup.py.

Run standalone for a readable report:
    python -m evals.test_spend_classification
Or under pytest:
    pytest evals/test_spend_classification.py -v
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from s3_measure.spend_classifier import classify_spend_line

_FIXTURE = Path(__file__).parent / "fixtures" / "spend_classification_cases.json"
_ADVERSARIAL = Path(__file__).parent / "fixtures" / "spend_classification_adversarial.json"

# Accuracy floors for this prototype. Set from the measured baseline; raise as
# the classifier improves. The point of A3 is to measure honestly, not to hit
# an invented bar.
_OVERALL_FLOOR = 0.85


def _load_cases() -> list[dict]:
    return json.loads(_FIXTURE.read_text())["cases"]


def _load_adversarial() -> list[dict]:
    return json.loads(_ADVERSARIAL.read_text())["cases"]


def _classify(case: dict):
    return classify_spend_line(case["description"], vendor=case.get("vendor"), amount_usd=1000.0)


def evaluate() -> dict:
    """Return a metrics dict (also used by the standalone report)."""
    cases = _load_cases()
    per_cat_total: dict[int, int] = defaultdict(int)
    per_cat_hit: dict[int, int] = defaultdict(int)
    misses: list[tuple[str, int, int]] = []
    flag_failures: list[str] = []

    for case in cases:
        exp = case["expected_category"]
        result = _classify(case)
        per_cat_total[exp] += 1
        if result.scope3_category == exp:
            per_cat_hit[exp] += 1
        else:
            misses.append((case["description"], exp, result.scope3_category))

        want_flag = case.get("expect_flag")
        if want_flag:
            flagged = result.flag_status != "ok"
            ok = flagged if want_flag == "any" else result.flag_status == want_flag
            if not ok:
                flag_failures.append(f"{case['description']!r} -> {result.flag_status}")

    total = sum(per_cat_total.values())
    hits = sum(per_cat_hit.values())
    return {
        "total": total,
        "hits": hits,
        "overall": hits / total if total else 0.0,
        "per_cat_total": dict(per_cat_total),
        "per_cat_hit": dict(per_cat_hit),
        "misses": misses,
        "flag_failures": flag_failures,
    }


def test_overall_accuracy_floor():
    m = evaluate()
    assert m["overall"] >= _OVERALL_FLOOR, (
        f"overall accuracy {m['overall']:.0%} below floor {_OVERALL_FLOOR:.0%}; "
        f"misses={m['misses']}"
    )


def test_flagged_lines_are_flagged():
    m = evaluate()
    assert not m["flag_failures"], f"flag expectations unmet: {m['flag_failures']}"


def test_determinism():
    cases = _load_cases()
    for case in cases:
        a = _classify(case)
        b = _classify(case)
        assert (a.scope3_category, a.eeio_sector_code, a.ef_kg_co2e_per_usd) == (
            b.scope3_category,
            b.eeio_sector_code,
            b.ef_kg_co2e_per_usd,
        ), f"non-deterministic classification for {case['description']!r}"


def adversarial_outcomes() -> dict:
    """Classify the adversarial set; bucket into correct / wrong-but-flagged /
    confident-wrong. The safety property is that confident-wrong == 0."""
    cases = _load_adversarial()
    correct = flagged = confident_wrong = 0
    offenders: list[str] = []
    for case in cases:
        r = classify_spend_line(case["description"], vendor=case.get("vendor"), amount_usd=1000.0)
        if r.scope3_category == case["expected_category"]:
            correct += 1
        elif r.flag_status != "ok":
            flagged += 1
        else:
            confident_wrong += 1
            offenders.append(f"{case['description']!r} -> Cat {r.scope3_category} (unflagged)")
    return {
        "total": len(cases),
        "correct": correct,
        "flagged": flagged,
        "confident_wrong": confident_wrong,
        "offenders": offenders,
    }


def test_adversarial_never_confidently_wrong():
    """The trust-critical invariant: on hard/ambiguous GL lines the classifier
    must be correct OR flag for human review — never a confident misclassify."""
    m = adversarial_outcomes()
    assert m["confident_wrong"] == 0, f"confident misclassifications: {m['offenders']}"


def test_every_matched_line_has_citation():
    cases = _load_cases()
    for case in cases:
        r = _classify(case)
        if r.flag_status != "no_match":
            assert r.ef_source, f"missing ef_source citation for {case['description']!r}"


def _report() -> None:
    m = evaluate()
    print(f"\nSpend classifier eval — {m['hits']}/{m['total']} = {m['overall']:.0%} overall\n")
    print("Per-category accuracy:")
    for cat in sorted(m["per_cat_total"]):
        hit, tot = m["per_cat_hit"].get(cat, 0), m["per_cat_total"][cat]
        print(f"  Cat {cat:>2}: {hit}/{tot}")
    if m["misses"]:
        print("\nMisses (description | expected -> got):")
        for desc, exp, got in m["misses"]:
            print(f"  {desc!r}  {exp} -> {got}")
    else:
        print("\nNo misses.")
    if m["flag_failures"]:
        print("\nFlag failures:")
        for f in m["flag_failures"]:
            print(f"  {f}")

    a = adversarial_outcomes()
    print(
        f"\nAdversarial set ({a['total']} hard lines): "
        f"correct={a['correct']} wrong-but-flagged={a['flagged']} "
        f"CONFIDENT-WRONG={a['confident_wrong']}"
    )
    safe = a["correct"] + a["flagged"]
    print(f"  SAFE (correct or flagged) = {safe}/{a['total']} = {safe / a['total']:.0%}")
    if a["offenders"]:
        print("  Confident misclassifications:")
        for o in a["offenders"]:
            print(f"    {o}")


if __name__ == "__main__":
    _report()
