"""Shared helpers for golden-file eval pipeline runs."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

from calc.critic import CriticReport, run_critic
from calc.footprint import FootprintResult, calculate_footprint
from factors.ef_lookup import EFMatch
from parsing.bom_parser import ParsedBOM, parse_bom_csv

GOLDEN_DIR = Path(__file__).parent / "golden_files"


def _ef_from_dict(data: dict[str, Any] | None) -> EFMatch | None:
    if data is None:
        return None
    return EFMatch(**data)


def load_golden_case(case_name: str) -> tuple[ParsedBOM, list[EFMatch | None], dict[str, Any]]:
    """Load a golden CSV and its expected EF fixture JSON."""
    csv_path = GOLDEN_DIR / f"{case_name}.csv"
    expected_path = GOLDEN_DIR / f"{case_name}.expected.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    bom = parse_bom_csv(csv_path, expected["product_name"])
    ef_matches = [_ef_from_dict(entry) for entry in expected["ef_matches"]]
    return bom, ef_matches, expected


def run_golden_pipeline(
    case_name: str,
) -> tuple[ParsedBOM, FootprintResult, CriticReport, dict[str, Any]]:
    """Run parse → calculate → critic for a golden case using fixture EF matches."""
    bom, ef_matches, expected = load_golden_case(case_name)
    result = calculate_footprint(bom, ef_matches)
    result, critic_report = run_critic(result)
    return bom, result, critic_report, expected


def serialize_result(result: FootprintResult) -> dict[str, Any]:
    """Serialize a FootprintResult for determinism comparisons."""
    return {
        "product_name": result.product_name,
        "total_kg_co2e": round(result.total_kg_co2e, 6),
        "matched_count": result.matched_count,
        "flagged_count": result.flagged_count,
        "unmatched_count": result.unmatched_count,
        "completeness_pct": round(result.completeness_pct, 4),
        "line_items": [
            {
                "row_index": li.row_index,
                "component": li.component,
                "material": li.material,
                "spend_usd": li.spend_usd,
                "kg_co2e": round(li.kg_co2e, 6),
                "share_pct": round(li.share_pct, 4),
                "ef_source": li.ef_source,
                "is_matched": li.is_matched,
                "is_low_confidence": li.is_low_confidence,
                "is_no_ef_match": li.is_no_ef_match,
                "is_flagged_by_parser": li.is_flagged_by_parser,
            }
            for li in result.line_items
        ],
    }


def assert_eval_invariants(result: FootprintResult) -> None:
    """Assert core eval invariants from CLAUDE.md."""
    matched_items = [li for li in result.line_items if li.is_matched]
    computed_total = sum(li.kg_co2e for li in matched_items)

    assert math.isclose(computed_total, result.total_kg_co2e, rel_tol=1e-9), (
        f"total_kg_co2e ({result.total_kg_co2e}) != sum of matched line items ({computed_total})"
    )

    for li in matched_items:
        assert li.spend_usd is not None and li.ef_kg_co2e_per_usd > 0
        expected_kg = li.spend_usd * li.ef_kg_co2e_per_usd
        assert math.isclose(li.kg_co2e, expected_kg, rel_tol=1e-9), (
            f"Row {li.row_index}: kg_co2e ({li.kg_co2e}) != spend_usd × EF ({expected_kg})"
        )
        assert li.ef_source.strip(), (
            f"Row {li.row_index}: matched line item missing ef_source citation"
        )

    for li in result.line_items:
        if li.is_no_ef_match and li.spend_usd and li.spend_usd > 0:
            assert not li.is_matched, (
                f"Row {li.row_index}: unmatched EF row should not be counted as matched"
            )


def assert_golden_expectations(result: FootprintResult, expected: dict[str, Any]) -> None:
    """Assert case-specific expectations from the golden JSON fixture."""
    exp = expected["expectations"]
    assert math.isclose(result.total_kg_co2e, exp["total_kg_co2e"], rel_tol=1e-6)
    assert result.matched_count == exp["matched_count"]
    assert result.unmatched_count == exp["unmatched_count"]

    flagged_rows = {idx for idx in exp.get("parser_flagged_rows", [])}
    for li in result.line_items:
        if li.row_index in flagged_rows:
            assert li.is_flagged_by_parser, (
                f"Row {li.row_index} expected parser flag but none found"
            )


def ef_match_to_dict(ef: EFMatch | None) -> dict[str, Any] | None:
    if ef is None:
        return None
    return asdict(ef)
