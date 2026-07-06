"""Unit tests for the Epic A GL/ERP spend parser (parsing/spend_parser.py).

Pure-logic, no DB/network. Exercises the sample GL file (which uses non-canonical
ERP headers) plus targeted edge cases for the CLAUDE.md decision rules.
"""

from __future__ import annotations

from pathlib import Path

from s3_measure.spend_parser import parse_spend_csv

_SAMPLE = Path(__file__).parent.parent / "sample_gl" / "company_gl_sample.csv"


def _parse_sample():
    return parse_spend_csv(_SAMPLE)


def _row(parsed, description_contains: str):
    return next(
        r for r in parsed.rows if description_contains.lower() in (r.description or "").lower()
    )


def _flag_types(row) -> set[str]:
    return {f.flag_type for f in row.flags}


def test_sample_parses_and_maps_headers():
    """Synonym mapping: 'Memo'->description, 'Amount'->amount_usd, etc."""
    parsed = _parse_sample()
    assert parsed.is_valid
    assert len(parsed.rows) == 12
    fabric = _row(parsed, "cotton knit fabric")
    assert fabric.description == "Cotton knit fabric - 500 yards"
    assert fabric.amount_usd == 12400.0
    assert fabric.vendor == "Piedmont Textiles"
    assert fabric.gl_account == "5010"


def test_missing_amount_flagged():
    parsed = _parse_sample()
    box = _row(parsed, "corrugated packaging")
    assert box.amount_usd is None
    assert "missing" in _flag_types(box)


def test_credit_negative_flagged():
    """Parenthesized accounting negative -> credit flag, value kept negative."""
    parsed = _parse_sample()
    refund = _row(parsed, "card processing fee refund")
    assert refund.amount_usd == -320.0
    assert "credit" in _flag_types(refund)


def test_duplicate_flagged():
    parsed = _parse_sample()
    dupes = [r for r in parsed.rows if "cotton knit fabric" in (r.description or "").lower()]
    assert len(dupes) == 2
    assert all("duplicate" in _flag_types(r) for r in dupes)


def test_non_usd_currency_flagged():
    parsed = _parse_sample()
    eu = _row(parsed, "linen fabric")
    assert eu.currency == "EUR"
    assert "currency" in _flag_types(eu)


def test_missing_description_flagged_error():
    """A blank Memo -> description None -> error flag (line can't be classified)."""
    parsed = _parse_sample()
    blank = next(r for r in parsed.rows if r.description is None)
    assert blank.vendor == "MysteryVendor"  # row exists, only description missing
    assert any(f.flag_type == "missing" and f.severity == "error" for f in blank.flags)


def test_anomalous_high_amount_flagged():
    parsed = _parse_sample()
    laptops = _row(parsed, "dell laptops")
    assert laptops.amount_usd == 1_250_000.0
    assert "anomalous" in _flag_types(laptops)


def test_money_formatting_normalized():
    """Commas and dollar formatting are stripped to a float."""
    parsed = _parse_sample()
    gas = _row(parsed, "natural gas")
    assert gas.amount_usd == 2150.0


def test_total_excludes_none_but_includes_credit():
    parsed = _parse_sample()
    # total is a plain sum of parsed amounts (credit is negative, missing is None)
    assert abs(parsed.total_amount_usd - _expected_total()) < 1e-6


def test_column_mapping_override():
    """An explicit mapping overrides/extends the synonym map."""
    csv = b"when,who,what,how_much\n2026-01-01,ACME,Steel coils,1000\n"
    parsed = parse_spend_csv(
        csv,
        column_mapping={"what": "description", "how_much": "amount_usd", "who": "vendor"},
    )
    assert parsed.is_valid
    assert parsed.rows[0].description == "Steel coils"
    assert parsed.rows[0].amount_usd == 1000.0


def test_unmappable_required_columns_errors():
    csv = b"foo,bar\n1,2\n"
    parsed = parse_spend_csv(csv)
    assert not parsed.is_valid
    assert any("required column" in e for e in parsed.file_errors)


def _expected_total() -> float:
    # 12400 + 12400 + 3250 + 8900 + 2150 + 1080 + (missing) + 5400 + 9800
    # + (-320 credit) + 1_250_000 + 640
    return 12400 + 12400 + 3250 + 8900 + 2150 + 1080 + 5400 + 9800 - 320 + 1_250_000 + 640
