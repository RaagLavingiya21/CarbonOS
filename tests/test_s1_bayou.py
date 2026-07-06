"""Tests for the Bayou client + mapping (HTTP injected — no live key needed)."""

from __future__ import annotations

import pytest

from s1_intake.bayou import BayouBill, BayouClient, BayouError, bayou_bill_to_extraction
from s1_intake.bayou.mapping import BAYOU_CONFIDENCE


def test_submit_bill_returns_id() -> None:
    calls = {}

    def fake_request(method, path, **kwargs):
        calls.update(method=method, path=path, files=bool(kwargs.get("files")))
        return {"id": 987}

    client = BayouClient(api_key="k", request=fake_request)
    assert client.submit_bill(b"pdf", "gas.pdf") == "987"
    assert calls == {"method": "POST", "path": "/bills", "files": True}


def test_get_bill_parses_fields() -> None:
    def fake_request(method, path, **kwargs):
        return {
            "has_been_parsed": True,
            "gas_consumption": "1000", "gas_consumption_unit": "therms",
            "billing_period_from": "2025-01-01", "billing_period_to": "2025-01-31",
            "gas_amount": "120.50", "account_number": "A-1", "meter_id": 42,
        }

    bill = BayouClient(api_key="k", request=fake_request).get_bill("987")
    assert bill.status == "parsed"
    assert bill.gas_consumption == 1000.0
    assert bill.gas_consumption_unit == "therms"
    assert bill.meter_id == "42"


def test_get_bill_still_parsing() -> None:
    bill = BayouClient(api_key="k", request=lambda *a, **k: {"has_been_parsed": False}).get_bill("1")
    assert bill.status == "parsing"
    assert bill.gas_consumption is None


def test_not_configured_raises_before_network() -> None:
    client = BayouClient(api_key="")           # no key, real transport
    assert client.is_configured is False
    with pytest.raises(BayouError):
        client.submit_bill(b"pdf")             # raises before any httpx call


def test_mapping_to_review_queue_shape() -> None:
    bill = BayouBill(
        bill_id="1", status="parsed", gas_consumption=1000.0, gas_consumption_unit="therms",
        billing_period_from="2025-01-01", billing_period_to="2025-01-31",
        gas_amount=120.5, account_number="A-1",
    )
    ext = bayou_bill_to_extraction(bill)
    # Same field names as the Claude utility-bill schema -> shared review UI.
    assert ext.fields["consumption_quantity"].value == "1000.0"
    assert ext.fields["consumption_unit"].value == "therms"
    assert ext.fields["billing_period_start"].value == "2025-01-01"
    assert ext.fields["consumption_quantity"].confidence == BAYOU_CONFIDENCE
    assert ext.model == "bayou"
    assert ext.needs_review() is False         # Tier-2 trusted
