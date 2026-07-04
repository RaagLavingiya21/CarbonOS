"""API tests for the Scope 1 routes.

Auth is bypassed by the autouse conftest fixture; store calls are monkeypatched
so no live Supabase is needed (same pattern as tests/test_api.py).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


def test_consolidation_preview_is_pure() -> None:
    resp = client.post(
        "/api/scope1/consolidation/preview",
        json={"approach": "equity_share", "economic_interest_pct": 40.0},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["multiplier"] == 0.40


def test_create_entity_delegates_to_store(monkeypatch) -> None:
    def fake_create_entity(data, *, access_token, user_id):
        return {"id": "e1", **data}

    monkeypatch.setattr("db.scope1_store.create_entity", fake_create_entity)
    resp = client.post(
        "/api/scope1/entities",
        json={"name": "Acme Mfg", "jurisdiction": "US", "entity_type": "parent",
              "effective_from": "2025-01-01"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "e1"
    assert resp.json()["name"] == "Acme Mfg"


def test_stationary_record_computes_gas_masses(monkeypatch) -> None:
    """The route runs the calc engine and persists gas masses (never CO2e)."""
    captured: dict = {}

    def fake_create_record(row, *, access_token, user_id):
        captured.update(row)
        return {"id": "rec1", **row}

    monkeypatch.setattr("db.scope1_store.create_record", fake_create_record)
    resp = client.post(
        "/api/scope1/records/stationary",
        json={
            "inventory_id": "inv1", "emission_source_id": "src1",
            "period_start": "2025-01-01", "period_end": "2025-01-31",
            "fuel_or_activity": "natural_gas", "activity_value": 1000,
            "activity_unit": "therms", "data_quality_tier": 2,
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert captured["kg_co2_fossil"] == 5306.0
    assert captured["kg_ch4"] == 0.100
    assert captured["kg_n2o"] == 0.010
    assert captured["biogenic_fossil_tag"] == "fossil"
    assert captured["ef_tier"] == "T1"
    assert "CFR" in captured["ef_source"]
    assert "kg_co2e" not in captured and "co2e" not in captured  # no CO2e stored


def test_stationary_record_unknown_fuel_returns_422(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.create_record", lambda row, **k: row)
    resp = client.post(
        "/api/scope1/records/stationary",
        json={"inventory_id": "inv1", "emission_source_id": "src1",
              "period_start": "2025-01-01", "period_end": "2025-01-31",
              "fuel_or_activity": "unobtanium", "activity_value": 10,
              "activity_unit": "mmBtu"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 422


def test_inventory_report_rollup(monkeypatch) -> None:
    record = {
        "id": "rec1", "inventory_id": "inv1", "emission_source_id": "src1",
        "kg_co2_fossil": 5306.0, "kg_ch4": 0.100, "kg_n2o": 0.010,
        "kg_co2_biogenic": 0.0,
    }
    monkeypatch.setattr("db.scope1_store.list_records_for_inventory",
                        lambda inv, **k: [record])
    monkeypatch.setattr("db.scope1_store.list_sources",
                        lambda **k: [{"id": "src1", "entity_id": "e1",
                                      "facility_id": "f1", "source_name": "Boiler 1"}])
    monkeypatch.setattr("db.scope1_store.list_facilities",
                        lambda **k: [{"id": "f1", "name": "Plant A"}])
    monkeypatch.setattr("db.scope1_store.list_boundaries",
                        lambda inv, **k: [{"entity_id": "e1", "consolidation_multiplier": 1.0}])

    resp = client.get("/api/scope1/inventories/inv1/report?ar_version=AR5", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_scope1_tco2e"] == round((5306.0 + 0.1 * 28 + 0.01 * 265) / 1000.0, 10)
    assert body["by_facility"][0]["facility_name"] == "Plant A"
    assert body["record_count"] == 1


def test_report_applies_consolidation_multiplier(monkeypatch) -> None:
    record = {"id": "rec1", "inventory_id": "inv1", "emission_source_id": "src1",
              "kg_co2_fossil": 1000.0, "kg_ch4": 0.0, "kg_n2o": 0.0, "kg_co2_biogenic": 0.0}
    monkeypatch.setattr("db.scope1_store.list_records_for_inventory", lambda inv, **k: [record])
    monkeypatch.setattr("db.scope1_store.list_sources",
                        lambda **k: [{"id": "src1", "entity_id": "e1", "facility_id": "f1",
                                      "source_name": "JV boiler"}])
    monkeypatch.setattr("db.scope1_store.list_facilities", lambda **k: [{"id": "f1", "name": "JV"}])
    monkeypatch.setattr("db.scope1_store.list_boundaries",
                        lambda inv, **k: [{"entity_id": "e1", "consolidation_multiplier": 0.40}])

    resp = client.get("/api/scope1/inventories/inv1/report", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    # 1000 kg CO2 x 0.40 = 0.4 tCO2e
    assert resp.json()["total_scope1_tco2e"] == 0.4
