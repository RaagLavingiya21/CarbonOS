"""Integration tests for Bayou credential-connect auto-pull (Priority 2).

These mock Bayou's API by injecting the client transport (`request`), so the
list -> parse -> map -> Extraction pipeline is exercised without a live key.
"""

from __future__ import annotations

from s1_intake.bayou import BayouClient, pull_parsed_extractions


def _client(response):
    """A BayouClient whose transport returns `response` for any request."""
    return BayouClient(api_key="test_key", request=lambda *a, **k: response)


def test_pull_maps_only_parsed_bills() -> None:
    bills = [
        {"id": 1, "status": "unlocked_for_gas", "gas_consumption": 120.0,
         "gas_consumption_unit": "therms", "billing_period_from": "2024-01-01",
         "billing_period_to": "2024-01-31", "meters": [{"id": 55}]},
        {"id": 2, "status": "locked"},                 # still parsing -> skipped
        {"id": 3, "status": "not_supported"},          # failed -> skipped
    ]
    result = pull_parsed_extractions(_client(bills))
    assert result.fetched == 3
    assert result.parsed_count == 1
    pulled = result.parsed[0]
    assert pulled.bill.bill_id == "1"
    assert pulled.bill.gas_consumption == 120.0
    # mapped to the shared extraction shape, ready to ingest
    assert pulled.extraction.to_dict()
    assert 0.0 <= pulled.extraction.min_confidence <= 1.0


def test_list_bills_handles_wrapped_response() -> None:
    client = _client({"bills": [{"id": 9, "status": "unlocked"}]})
    bills = client.list_bills()
    assert len(bills) == 1
    assert bills[0].bill_id == "9"
    assert bills[0].status == "parsed"


def test_pull_empty_account() -> None:
    result = pull_parsed_extractions(_client([]))
    assert result.fetched == 0
    assert result.parsed_count == 0
    assert result.parsed == []
