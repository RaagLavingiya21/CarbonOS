"""Tests for Scope 2 CSV bulk import (PRD 5.1)."""

from __future__ import annotations

from datetime import date

import pytest

from s2_ingestion.csv_import import (
    ColumnMappingError,
    import_bills_csv,
)

MAPPING = {
    "site_ref": "Store",
    "period_start": "From",
    "period_end": "To",
    "quantity": "Usage",
    "unit": "Unit",
    "cost_usd": "Cost",
    "is_estimated": "Estimated",
}


def test_valid_rows_normalize_to_mwh() -> None:
    csv_text = (
        "Store,From,To,Usage,Unit,Cost,Estimated\n"
        "S1,2022-01-01,2022-01-31,1500,kWh,220.50,false\n"
    )
    result = import_bills_csv(csv_text, MAPPING)
    assert not result.errors
    bill = result.bills[0]
    assert bill.site_ref == "S1"
    assert bill.period_start == date(2022, 1, 1)
    assert bill.canonical_mwh == pytest.approx(1.5)
    assert bill.cost_usd == pytest.approx(220.50)
    assert bill.is_cost_only is False


def test_cost_only_row_is_flagged_not_errored() -> None:
    csv_text = "Store,From,To,Usage,Unit,Cost,Estimated\nS1,2022-01-01,2022-01-31,,,88.00,false\n"
    result = import_bills_csv(csv_text, MAPPING)
    assert not result.errors
    bill = result.bills[0]
    assert bill.is_cost_only is True
    assert bill.canonical_mwh is None  # never treated as kWh
    assert bill.cost_usd == pytest.approx(88.00)


def test_bad_unit_becomes_row_error_not_crash() -> None:
    csv_text = "Store,From,To,Usage,Unit,Cost,Estimated\nS1,2022-01-01,2022-01-31,10,MBtu,5,false\n"
    result = import_bills_csv(csv_text, MAPPING)
    assert result.bills == []
    assert len(result.errors) == 1
    assert "ambiguous" in result.errors[0].message.lower()


def test_bad_date_becomes_row_error() -> None:
    csv_text = "Store,From,To,Usage,Unit,Cost,Estimated\nS1,not-a-date,2022-01-31,10,kWh,5,false\n"
    result = import_bills_csv(csv_text, MAPPING)
    assert len(result.errors) == 1


def test_missing_required_mapping_raises() -> None:
    with pytest.raises(ColumnMappingError):
        import_bills_csv("x\n1\n", {"site_ref": "x"})


def test_estimated_flag_parsed() -> None:
    csv_text = "Store,From,To,Usage,Unit,Cost,Estimated\nS1,2022-01-01,2022-01-31,1000,kWh,5,yes\n"
    result = import_bills_csv(csv_text, MAPPING)
    assert result.bills[0].is_estimated_read is True
