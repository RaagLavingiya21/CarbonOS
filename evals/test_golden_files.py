"""Golden-file eval tests — run Spec BOM examples through the analyzer pipeline.

Each case uses deterministic EF fixture JSON so CI does not depend on the Open CEDA
Excel file. Assertions cover eval invariants from CLAUDE.md:
  - total = sum of matched line items
  - kg_co2e = spend_usd × ef_kg_co2e_per_usd
  - every matched EF has a source citation
  - same input → same output (determinism)
"""

from __future__ import annotations

import pytest

from evals.helpers import (
    assert_eval_invariants,
    assert_golden_expectations,
    run_golden_pipeline,
    serialize_result,
)

GOLDEN_CASES = ["clean_tshirt", "messy_tshirt", "water_bottle"]


@pytest.mark.parametrize("case_name", GOLDEN_CASES)
def test_golden_file_invariants(case_name: str) -> None:
    """Each golden BOM satisfies core eval invariants after full pipeline run."""
    _, result, _, expected = run_golden_pipeline(case_name)
    assert_eval_invariants(result)
    assert_golden_expectations(result, expected)


@pytest.mark.parametrize("case_name", GOLDEN_CASES)
def test_golden_file_determinism(case_name: str) -> None:
    """Same golden input produces identical serialized output on repeated runs."""
    _, result_a, _, _ = run_golden_pipeline(case_name)
    _, result_b, _, _ = run_golden_pipeline(case_name)
    assert serialize_result(result_a) == serialize_result(result_b)


@pytest.mark.parametrize("case_name", GOLDEN_CASES)
def test_golden_file_matched_rows_have_citations(case_name: str) -> None:
    """Every matched line item must cite its emission factor source."""
    _, result, _, _ = run_golden_pipeline(case_name)
    for li in result.line_items:
        if li.is_matched:
            assert li.ef_source, (
                f"Row {li.row_index} ({li.material}): missing ef_source on matched row"
            )
            assert "Open CEDA" in li.ef_source or li.ef_source.startswith("Test"), (
                f"Row {li.row_index}: ef_source should reference Open CEDA database"
            )


def test_clean_tshirt_no_parser_flags() -> None:
    """Clean T-shirt BOM from Specs should parse without flags."""
    bom, _, _, expected = run_golden_pipeline("clean_tshirt")
    assert bom.is_valid
    assert bom.all_flags == []
    assert expected["expectations"]["parser_flagged_rows"] == []


def test_messy_tshirt_flags_missing_fields() -> None:
    """Messy T-shirt BOM flags missing material and spend_usd per Spec."""
    bom, _, _, _ = run_golden_pipeline("messy_tshirt")
    row0_flags = [f for f in bom.rows[0].flags if f.field == "material"]
    row1_flags = [f for f in bom.rows[1].flags if f.field == "spend_usd"]
    assert row0_flags, "Row 1 should be flagged for missing material"
    assert row1_flags, "Row 2 should be flagged for missing spend_usd"


def test_water_bottle_unmatched_materials() -> None:
    """Water bottle edge case flags aerogel and tritan as unmatched per Spec."""
    _, result, _, _ = run_golden_pipeline("water_bottle")
    aerogel = result.line_items[3]
    tritan = result.line_items[4]
    assert aerogel.is_no_ef_match
    assert tritan.is_no_ef_match
    assert not aerogel.is_matched
    assert not tritan.is_matched
