from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest

from calc.dqr import CEDA_VINTAGE_YEAR, aggregate_dqr, line_item_dqr
from calc.footprint import FootprintResult, LineItem
from db import store as store_module
from exchange.pact import build_product_footprint, validate_product_footprint
from tests.conftest import TEST_ACCESS_TOKEN, TEST_USER_ID

SCHEMA_PATH = Path(__file__).resolve().parent / "fixtures" / "pact_v3_product_footprint_schema.json"


@pytest.fixture
def pact_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def test_line_item_dqr_primary_technological_is_one() -> None:
    dqr = line_item_dqr(
        ef_confidence=50.0,
        is_low_confidence=True,
        data_source="primary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR,
    )
    assert dqr["technological"] == 1


def test_line_item_dqr_confidence_bands() -> None:
    assert line_item_dqr(
        ef_confidence=95.0,
        is_low_confidence=False,
        data_source="secondary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR,
    )["technological"] == 2
    assert line_item_dqr(
        ef_confidence=80.0,
        is_low_confidence=False,
        data_source="secondary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR,
    )["technological"] == 3
    assert line_item_dqr(
        ef_confidence=65.0,
        is_low_confidence=False,
        data_source="secondary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR,
    )["technological"] == 4
    assert line_item_dqr(
        ef_confidence=40.0,
        is_low_confidence=True,
        data_source="secondary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR,
    )["technological"] == 5


def test_line_item_dqr_geographical_with_country() -> None:
    dqr = line_item_dqr(
        ef_confidence=90.0,
        is_low_confidence=False,
        data_source="secondary",
        country_of_origin="CN",
        reporting_year=CEDA_VINTAGE_YEAR,
    )
    assert dqr["geographical"] == 2
    assert line_item_dqr(
        ef_confidence=90.0,
        is_low_confidence=False,
        data_source="secondary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR,
    )["geographical"] == 4


def test_line_item_dqr_temporal_by_reporting_year() -> None:
    assert line_item_dqr(
        ef_confidence=90.0,
        is_low_confidence=False,
        data_source="secondary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR,
    )["temporal"] == 1
    assert line_item_dqr(
        ef_confidence=90.0,
        is_low_confidence=False,
        data_source="secondary",
        country_of_origin=None,
        reporting_year=CEDA_VINTAGE_YEAR - 4,
    )["temporal"] == 3


def test_aggregate_dqr_weighted_by_kg_co2e() -> None:
    items = [
        {
            "kg_co2e": 80.0,
            "technological_dqr": 2,
            "geographical_dqr": 4,
            "temporal_dqr": 1,
        },
        {
            "kg_co2e": 20.0,
            "technological_dqr": 5,
            "geographical_dqr": 2,
            "temporal_dqr": 1,
        },
    ]
    aggregate = aggregate_dqr(items)
    assert aggregate["technological"] == 3
    assert aggregate["geographical"] == 4
    assert aggregate["temporal"] == 1


def test_pact_dqi_matches_computed_aggregate_not_hardcoded_four(pact_schema: dict) -> None:
    product = {
        "product_id": 42,
        "user_id": TEST_USER_ID,
        "product_name": "DQR Product",
        "product_description": "Test",
        "analysis_date": "2025-06-15",
        "total_kg_co2e": 100.0,
        "matched_items": 2,
        "flagged_items": 0,
        "status": "approved",
        "footprint_uuid": str(uuid4()),
        "declared_unit": "piece",
        "unitary_product_amount": 1.0,
        "system_boundary": "cradle-to-gate",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "geography_country": None,
        "primary_data_share": 0.0,
        "spec_version": "3.0.0",
        "technological_dqr": 2,
        "geographical_dqr": 3,
        "temporal_dqr": 1,
        "line_items": [],
    }
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")
    dqi = payload["pcf"]["dqi"]
    assert dqi["technologicalDQR"] == "2"
    assert dqi["geographicalDQR"] == "3"
    assert dqi["temporalDQR"] == "1"
    assert not (dqi["technologicalDQR"] == "4" and dqi["geographicalDQR"] == "4" and dqi["temporalDQR"] == "4")
    assert validate_product_footprint(payload) == []
    jsonschema.validate(instance=payload, schema=pact_schema)


def test_save_analysis_persists_dqr_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {"line_items": []}

    def fake_table(name: str):
        from unittest.mock import MagicMock

        mock_table = MagicMock()
        if name == "products":

            def capture_insert(data: dict):
                captured["product"] = data
                mock_insert = MagicMock()
                mock_insert.execute.return_value = MagicMock(data=[{"product_id": 99}])
                return mock_insert

            mock_table.insert = capture_insert
        elif name == "line_items":

            def capture_items(data: list[dict]):
                captured["line_items"] = data
                mock_insert = MagicMock()
                mock_insert.execute.return_value = MagicMock(data=[])
                return mock_insert

            mock_table.insert = capture_items
        return mock_table

    from unittest.mock import MagicMock

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)

    line_item = LineItem(
        row_index=0,
        component="body",
        material="cotton",
        quantity=1.0,
        spend_usd=10.0,
        weight_kg=None,
        supplier=None,
        country_of_origin="US",
        sector_name="Cotton",
        sector_code="111",
        ef_kg_co2e_per_usd=2.0,
        ef_source="Open CEDA 2025",
        ef_confidence=92.0,
        kg_co2e=20.0,
        share_pct=100.0,
        is_matched=True,
        is_low_confidence=False,
        is_no_ef_match=False,
        is_flagged_by_parser=False,
    )
    result = FootprintResult(
        product_name="DQR Test",
        total_kg_co2e=20.0,
        line_items=[line_item],
        matched_count=1,
        flagged_count=0,
        unmatched_count=0,
        completeness_pct=100.0,
    )

    store_module.save_analysis(
        "DQR Test",
        result,
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
        reporting_period_start=date(CEDA_VINTAGE_YEAR, 1, 1),
        reporting_period_end=date(CEDA_VINTAGE_YEAR, 12, 31),
    )

    assert captured["product"]["technological_dqr"] is not None
    assert captured["product"]["dqr_computed_at"]
    assert captured["line_items"][0]["technological_dqr"] == 2
    assert captured["line_items"][0]["geographical_dqr"] == 2
    assert captured["line_items"][0]["ef_confidence"] == 92.0
