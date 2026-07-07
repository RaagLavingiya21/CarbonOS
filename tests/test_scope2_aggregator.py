"""Tests for the Scope 2 aggregator adapter (PRD 5.1)."""

from __future__ import annotations

from datetime import date

import pytest

from s2_ingestion.aggregator import (
    AggregatorError,
    FakeAggregatorProvider,
    RawBill,
    RawUtilityAccount,
    get_provider,
    map_raw_bill,
    register_provider,
)
from s2_ingestion.normalize import UnitConversionError


def test_map_raw_bill_normalizes_to_mwh() -> None:
    raw = RawBill(
        provider_account_ref="acct-1",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        quantity=1500.0,
        unit="kWh",
        cost_usd=210.0,
        provider_record_ref="rec-9",
    )
    row = map_raw_bill(raw, account_id=7)
    assert row["account_id"] == 7
    assert row["canonical_mwh"] == pytest.approx(1.5)
    assert row["is_cost_only"] is False
    assert row["ingestion_method"] == "aggregator"
    assert row["source_ref"] == "rec-9"
    assert row["period_start"] == "2025-01-01"


def test_map_raw_bill_cost_only_has_no_mwh() -> None:
    raw = RawBill(
        provider_account_ref="acct-1",
        period_start=date(2025, 2, 1),
        period_end=date(2025, 2, 28),
        quantity=None,
        unit=None,
        cost_usd=95.0,
    )
    row = map_raw_bill(raw, account_id=7)
    assert row["is_cost_only"] is True
    assert row["canonical_mwh"] is None
    assert row["cost_usd"] == 95.0


def test_map_raw_bill_preserves_estimated_flag() -> None:
    raw = RawBill(
        provider_account_ref="acct-1",
        period_start=date(2025, 3, 1),
        period_end=date(2025, 3, 31),
        quantity=1000.0,
        unit="kWh",
        is_estimated_read=True,
    )
    assert map_raw_bill(raw, account_id=1)["is_estimated_read"] is True


def test_map_raw_bill_rejects_bad_unit() -> None:
    raw = RawBill(
        provider_account_ref="acct-1",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        quantity=10.0,
        unit="mbtu",  # ambiguous -> must raise, never silently assumed
    )
    with pytest.raises(UnitConversionError):
        map_raw_bill(raw, account_id=1)


def test_fake_provider_serves_accounts_and_date_filtered_bills() -> None:
    provider = FakeAggregatorProvider(
        accounts={"conn-1": [RawUtilityAccount(provider_account_ref="acct-1")]},
        bills={
            "acct-1": [
                RawBill("acct-1", date(2025, 1, 1), date(2025, 1, 31), 1000.0, "kWh"),
                RawBill("acct-1", date(2025, 6, 1), date(2025, 6, 30), 1200.0, "kWh"),
            ]
        },
    )
    assert [a.provider_account_ref for a in provider.fetch_accounts("conn-1")] == ["acct-1"]
    in_range = provider.fetch_bills(
        "acct-1", start=date(2025, 1, 1), end=date(2025, 3, 31)
    )
    assert len(in_range) == 1
    assert in_range[0].period_start == date(2025, 1, 1)


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(AggregatorError):
        get_provider("arcadia")  # not wired until a design partner fixes the choice


def test_register_then_get_provider() -> None:
    provider = FakeAggregatorProvider(name="unit-test-fake")
    register_provider(provider)
    assert get_provider("unit-test-fake") is provider
