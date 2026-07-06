"""Tests for the Scope 1 CSV bulk-intake parser (pure, DB-free)."""

from __future__ import annotations

from s1_intake import parse_intake_csv


def test_parse_valid_rows() -> None:
    data = (
        b"source_name,category,fuel,amount,unit\n"
        b"Boiler 1,stationary,natural_gas,1000,therms\n"
        b"Van,mobile,motor_gasoline,400,gal\n"
    )
    parsed = parse_intake_csv(data)
    assert parsed.file_errors == []
    assert len(parsed.valid_rows) == 2
    first = parsed.rows[0]
    assert first.row_index == 2                      # header is line 1
    assert first.category == "stationary"
    assert first.source_name == "Boiler 1"
    assert first.amount == 1000.0
    assert first.unit == "therms"
    assert first.tier == 4                           # default


def test_missing_required_columns() -> None:
    parsed = parse_intake_csv(b"source_name,category\nx,stationary\n")
    assert parsed.rows == []
    assert parsed.file_errors and "Missing required columns" in parsed.file_errors[0]


def test_row_level_validation() -> None:
    data = (
        b"source_name,category,fuel,amount,unit\n"
        b",stationary,natural_gas,-5,therms\n"        # missing name + non-positive amount
        b"Boiler,rocket,natural_gas,10,therms\n"      # bad category
    )
    parsed = parse_intake_csv(data)
    assert parsed.valid_rows == []
    assert any("source_name" in e for e in parsed.rows[0].errors)
    assert any("amount" in e for e in parsed.rows[0].errors)
    assert any("category" in e for e in parsed.rows[1].errors)


def test_optional_fields_and_biogenic() -> None:
    data = (
        b"source_name,category,fuel,amount,unit,miles,model_year,tier,biogenic\n"
        b"Car,mobile,motor_gasoline,400,gal,10000,2022,2,no\n"
        b"Gen,stationary,biodiesel_b100,50,gal,,,3,yes\n"
    )
    rows = parse_intake_csv(data).rows
    assert rows[0].miles == 10000.0 and rows[0].model_year == 2022
    assert rows[0].tier == 2 and rows[0].biogenic is False
    assert rows[1].biogenic is True


def test_bad_tier_flagged() -> None:
    data = b"source_name,category,fuel,amount,unit,tier\nB,stationary,natural_gas,10,therms,9\n"
    row = parse_intake_csv(data).rows[0]
    assert any("tier" in e for e in row.errors)
