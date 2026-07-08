"""Deterministic eval for the Epic B question->datapoint mapper (P.4.2.2).

The headline invariant is NO FABRICATED NUMBERS: every numeric answer equals an
inventory datapoint, and anything unmappable is flagged needs_human with a null
value. Also checks correct category/total mapping, out-of-scope handling, and
determinism. No DB / API key / network.
"""

from __future__ import annotations

import json
from pathlib import Path

from s3_questionnaire.models import ParsedQuestion
from s3_questionnaire.question_mapper import map_question

_FIXTURE = Path(__file__).parent / "fixtures" / "question_mapping_cases.json"


def _load():
    data = json.loads(_FIXTURE.read_text())
    inv = data["inventory"]
    inventory = {
        "total": inv["total"],
        "categories": {int(k): v for k, v in inv["categories"].items()},
    }
    return inventory, data["cases"]


def _q(case: dict, i: int) -> ParsedQuestion:
    return ParsedQuestion(
        index=i,
        text=case["text"],
        question_type=case["question_type"],
        framework_field_key=case.get("framework_field_key"),
    )


def test_maps_expected_refs():
    inventory, cases = _load()
    for i, case in enumerate(cases):
        m = map_question(_q(case, i), inventory)
        assert m.datapoint_ref == case["expected_ref"], (
            f"{case['text']!r} -> {m.datapoint_ref} (expected {case['expected_ref']})"
        )


def test_no_fabricated_numbers():
    """THE invariant: a value is present only when it equals a real datapoint;
    everything else is flagged needs_human with a null value."""
    inventory, cases = _load()
    datapoints = {"inventory:total": inventory["total"]}
    for cat, val in inventory["categories"].items():
        datapoints[f"inventory:cat{cat}.total"] = val

    for i, case in enumerate(cases):
        m = map_question(_q(case, i), inventory)
        if m.mapped_value is None:
            assert m.flag_status == "needs_human", f"{case['text']!r} null value not flagged"
        else:
            # a mapped number must EXACTLY equal the datapoint it cites
            assert m.datapoint_ref in datapoints, f"{case['text']!r} unknown ref {m.datapoint_ref}"
            assert m.mapped_value == datapoints[m.datapoint_ref]
            assert case["expected_ref"] is not None  # only the expected-mapped cases get values


def test_expected_values_match():
    inventory, cases = _load()
    for i, case in enumerate(cases):
        if case.get("expected_value") is None:
            continue
        m = map_question(_q(case, i), inventory)
        assert m.mapped_value == case["expected_value"]


def test_unmappable_and_non_numeric_flagged():
    inventory, cases = _load()
    for i, case in enumerate(cases):
        if case["expected_ref"] is not None:
            continue
        m = map_question(_q(case, i), inventory)
        assert m.flag_status == "needs_human"
        assert m.mapped_value is None


def test_determinism():
    inventory, cases = _load()
    for i, case in enumerate(cases):
        a = map_question(_q(case, i), inventory)
        b = map_question(_q(case, i), inventory)
        assert (a.datapoint_ref, a.mapped_value, a.flag_status) == (
            b.datapoint_ref,
            b.mapped_value,
            b.flag_status,
        )
