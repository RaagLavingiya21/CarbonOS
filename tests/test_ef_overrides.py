"""Tests for EF overrides, sector search, and line-item re-map."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db import ef_override_store as override_store_module
from db import store as store_module
from factors.ef_lookup import lookup_ef, normalize_material, search_sectors
from tests.conftest import AUTH_HEADERS, TEST_ACCESS_TOKEN, TEST_USER_ID

client = TestClient(app)

LINEAGE_A = "11111111-1111-1111-1111-111111111111"
ORG_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def test_migration_029_defines_ef_overrides_table() -> None:
    sql = Path("supabase/migrations/029_ef_overrides.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS ef_overrides" in sql
    assert "ef_overrides_org_material_uidx" in sql
    assert "ef_overrides_user_material_uidx" in sql
    assert "ENABLE ROW LEVEL SECURITY" in sql
    assert "ef_overrides_select_org" in sql
    assert "ef_overrides_select_personal" in sql


def test_lookup_ef_with_override_returns_confidence_100() -> None:
    material = "mystery polymer blend"
    sector_code = "315000"
    overrides = {normalize_material(material): sector_code}

    match = lookup_ef(material, "US", overrides=overrides)

    assert match.is_no_match is False
    assert match.is_low_confidence is False
    assert match.confidence_score == 100.0
    assert match.sector_code == sector_code
    assert "Analyst override" in match.source_citation


def test_search_sectors_returns_matches() -> None:
    results = search_sectors("textile", limit=5)
    assert results
    assert any("textile" in name.lower() for _, name in results)


def test_get_active_overrides_is_org_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeOrg:
        id = ORG_ID

    captured: dict = {}

    def fake_table(name: str) -> MagicMock:
        mock_table = MagicMock()
        mock_execute = MagicMock(
            data=[{"material_normalized": "cotton", "sector_code": "315000"}]
        )
        mock_eq = MagicMock()
        mock_eq.execute = MagicMock(return_value=mock_execute)
        mock_select = MagicMock()
        mock_select.eq = MagicMock(return_value=mock_eq)
        mock_table.select = MagicMock(return_value=mock_select)
        captured["table"] = name
        return mock_table

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(override_store_module, "get_active_org", lambda *_args, **_kwargs: FakeOrg())
    monkeypatch.setattr(override_store_module, "get_user_client", lambda _token: mock_client)

    overrides = override_store_module.get_active_overrides(
        TEST_ACCESS_TOKEN,
        user_id=TEST_USER_ID,
    )

    assert captured["table"] == "ef_overrides"
    assert overrides == {"cotton": "315000"}


def _source_product_with_low_confidence_line() -> dict:
    return {
        "product_id": 5,
        "product_name": "Test Product",
        "analysis_date": "2025-06-15",
        "total_kg_co2e": 20.0,
        "matched_items": 1,
        "flagged_items": 1,
        "status": "published",
        "flagged_comment": None,
        "product_description": "Desc",
        "declared_unit": "piece",
        "unitary_product_amount": 1.0,
        "system_boundary": "cradle-to-gate",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "geography_country": None,
        "primary_data_share": 0.0,
        "spec_version": "3.0.0",
        "product_lineage_id": LINEAGE_A,
        "version": 1,
        "line_items": [
            {
                "item_id": 10,
                "component": "body",
                "material": "mystery polymer blend",
                "spend_usd": 10.0,
                "matched_sector": "Wrong sector",
                "emission_factor": 2.0,
                "ef_source": "CEDA fuzzy",
                "ef_confidence": 65.0,
                "kg_co2e": 20.0,
                "share_pct": 100.0,
                "flag_status": "low_confidence",
                "data_source": "secondary",
                "country_of_origin": "US",
            },
        ],
    }


def test_remap_line_creates_new_version_without_mutating_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_product_with_low_confidence_line()
    source_snapshot = {
        "product": dict(source),
        "line_items": [dict(li) for li in source["line_items"]],
    }
    product_inserts: list[dict] = []
    line_item_inserts: list[list[dict]] = []

    def fake_table(name: str) -> MagicMock:
        mock_table = MagicMock()
        if name == "products":
            mock_insert = MagicMock()
            mock_execute = MagicMock()

            def capture_insert(data: dict) -> MagicMock:
                product_inserts.append(data)
                mock_execute.data = [{"product_id": 102}]
                mock_insert.execute = MagicMock(return_value=mock_execute)
                return mock_insert

            mock_table.insert = capture_insert
        elif name == "line_items":
            mock_insert = MagicMock()
            mock_execute = MagicMock()

            def capture_insert(rows: list[dict]) -> MagicMock:
                line_item_inserts.append(rows)
                mock_insert.execute = MagicMock(return_value=mock_execute)
                return mock_insert

            mock_table.insert = capture_insert
        elif name == "audit_log":
            mock_table.insert.return_value.execute.return_value = MagicMock(data=[])
        return mock_table

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(store_module, "get_product_by_id", lambda pid, token: source if pid == 5 else None)
    monkeypatch.setattr(store_module, "append_audit_log", lambda **_kwargs: None)

    result = store_module.remap_line_item(
        5,
        10,
        "315000",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )

    assert result["new_product_id"] == 102
    assert result["version"] == 2
    assert result["total_kg_co2e_before"] == 20.0
    assert result["total_kg_co2e_after"] != 20.0
    assert result["delta_kg_co2e"] == pytest.approx(result["total_kg_co2e_after"] - 20.0)

    remapped_row = line_item_inserts[0][0]
    assert remapped_row["matched_sector"]
    assert remapped_row["ef_confidence"] == 100.0
    assert "re-map" in (remapped_row["ef_source"] or "").lower()
    assert remapped_row["flag_status"] == "ok"

    assert product_inserts[0]["version"] == 2
    assert product_inserts[0]["product_lineage_id"] == LINEAGE_A

    assert source_snapshot["product"]["version"] == 1
    assert source_snapshot["product"]["status"] == "published"
    assert source_snapshot["line_items"][0]["kg_co2e"] == 20.0


def test_remap_line_api_returns_new_version(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.routes.factors.get_product_by_id",
        lambda product_id, access_token: _source_product_with_low_confidence_line(),
    )
    monkeypatch.setattr(
        "api.routes.factors.remap_line_item",
        lambda source_product_id, item_id, sector_code, **kwargs: {
            "new_product_id": 102,
            "version": 2,
            "total_kg_co2e_before": 20.0,
            "total_kg_co2e_after": 18.5,
            "delta_kg_co2e": -1.5,
            "remapped_item_id": item_id,
            "sector_code": sector_code,
            "sector_name": "Apparel manufacturing",
        },
    )

    response = client.post(
        "/api/analyses/5/remap-line",
        json={"item_id": 10, "sector_code": "315000", "save_override": False},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["new_product_id"] == 102
    assert payload["version"] == 2
    assert payload["delta_kg_co2e"] == -1.5


def test_sector_search_endpoint_returns_results() -> None:
    response = client.get("/api/factors/sectors?q=textile", headers=AUTH_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    assert payload
    assert "sector_code" in payload[0]
    assert "sector_name" in payload[0]


def test_override_then_lookup_uses_saved_mapping() -> None:
    material = "mystery polymer blend"
    sector_code = "315000"
    overrides = {normalize_material(material): sector_code}
    first = lookup_ef(material, None, overrides=None)
    second = lookup_ef(material, None, overrides=overrides)

    assert first.sector_code != second.sector_code or first.confidence_score < 100.0
    assert second.confidence_score == 100.0
    assert second.sector_code == sector_code
