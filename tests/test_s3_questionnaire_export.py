"""Tests for the Epic B questionnaire export packs (P.4.2.6). Pure logic."""

from __future__ import annotations

import csv
import io

import pytest

from s3_questionnaire.exporter import _NEEDS_HUMAN, AnswerRow, export_pack, to_csv, to_markdown

_ANSWERS = [
    AnswerRow(
        question_text="Gross global Scope 3 emissions?",
        question_type="numeric",
        framework_field_key="cdp.C6.5",
        answer_text="100000 kg CO2e",
        datapoint_ref="inventory:total",
        citation="Scope 3 corporate inventory (inventory:total)",
        confidence_score=95.0,
        flag_status="ok",
    ),
    AnswerRow(
        question_text="What were your Scope 1 emissions?",
        question_type="numeric",
        framework_field_key=None,
        answer_text=None,
        datapoint_ref=None,
        citation=None,
        confidence_score=0.0,
        flag_status="needs_human",
    ),
    AnswerRow(
        question_text="Describe your reduction initiatives.",
        question_type="narrative",
        framework_field_key=None,
        answer_text=None,
        datapoint_ref=None,
        citation=None,
        confidence_score=0.0,
        flag_status="needs_human",
    ),
]


def _csv_rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


def test_csv_has_header_and_row_per_answer():
    rows = _csv_rows(to_csv(_ANSWERS))
    assert rows[0] == ["field_key", "question", "type", "answer", "citation", "confidence", "flag"]
    assert len(rows) == 1 + len(_ANSWERS)


def test_answered_row_has_value_and_citation():
    rows = _csv_rows(to_csv(_ANSWERS))
    answered = rows[1]  # first data row = the Scope 3 total
    assert answered[3] == "100000 kg CO2e"
    assert "inventory:total" in answered[4]
    assert answered[6] == "ok"


def test_needs_human_rows_never_carry_a_value():
    """The no-fabrication invariant, enforced in the exported artifact."""
    rows = _csv_rows(to_csv(_ANSWERS))
    for row in rows[1:]:
        answer_cell, flag = row[3], row[6]
        if flag == "needs_human":
            assert answer_cell == _NEEDS_HUMAN
            assert row[4] == "" and row[5] == ""  # no citation, no confidence


def test_markdown_counts_and_placeholder():
    md = to_markdown(_ANSWERS, title="ACME CDP 2026")
    assert "# ACME CDP 2026" in md
    assert "1 of 3 questions answered" in md
    assert _NEEDS_HUMAN in md
    assert "inventory:total" in md  # citation present for the answered one


def test_export_pack_dispatch_and_bad_format():
    assert export_pack(_ANSWERS, "csv").startswith("field_key")
    assert export_pack(_ANSWERS, "markdown").startswith("# ")
    with pytest.raises(ValueError):
        export_pack(_ANSWERS, "pdf")


def test_determinism():
    assert to_csv(_ANSWERS) == to_csv(_ANSWERS)
    assert to_markdown(_ANSWERS) == to_markdown(_ANSWERS)
