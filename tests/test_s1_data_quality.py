"""Tests for data-quality tier reporting + member emails on the Team page."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from s1_reporting import build_tier_breakdown
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def _role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")


# --- Pure tier breakdown ----------------------------------------------------

def test_build_tier_breakdown_shares_and_counts() -> None:
    tb = build_tier_breakdown([(1, 72.0), (1, 8.0), (5, 20.0)])
    assert tb.total_count == 3
    assert tb.total_tco2e == 100.0
    by_tier = {r.tier: r for r in tb.rows}
    assert by_tier[1].count == 2 and by_tier[1].tco2e == 80.0 and by_tier[1].pct == 80.0
    assert by_tier[5].count == 1 and by_tier[5].pct == 20.0
    assert [r.tier for r in tb.rows] == [1, 5]        # sorted ascending
    assert by_tier[1].label == "Measured (CEMS/meter)"


def test_build_tier_breakdown_empty_no_divide_error() -> None:
    tb = build_tier_breakdown([])
    assert tb.rows == [] and tb.total_tco2e == 0.0 and tb.total_count == 0


# --- Route: all three categories fold into the mix --------------------------

def _mock_records(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_records_for_inventory", lambda inv, **k: [
        {"id": "r1", "emission_source_id": "s1", "data_quality_tier": 1,
         "kg_co2_fossil": 100000.0, "kg_ch4": 0.0, "kg_n2o": 0.0, "kg_co2_biogenic": 0.0}])
    monkeypatch.setattr("db.scope1_store.list_sources", lambda **k: [
        {"id": "s1", "entity_id": "e1", "facility_id": "f1", "source_name": "Boiler",
         "primary_fuel": "natural_gas"}])
    monkeypatch.setattr("db.scope1_store.list_facilities", lambda **k: [{"id": "f1", "name": "Plant A"}])
    monkeypatch.setattr("db.scope1_store.list_boundaries", lambda inv, **k: [
        {"entity_id": "e1", "consolidation_multiplier": 1.0}])
    monkeypatch.setattr("db.scope1_store.list_fugitive_records", lambda inv, **k: [
        {"id": "fg1", "refrigerant": "R-410A", "leaked_kg": 10.0, "facility_id": "f1",
         "data_quality_tier": 4}])
    monkeypatch.setattr("db.scope1_store.list_process_records", lambda inv, **k: [
        {"id": "pr1", "process_type": "cement_clinker", "gas_species": "Carbon dioxide",
         "emission_kg": 2000.0, "facility_id": "f1", "data_quality_tier": 5}])


def test_data_quality_route_spans_all_categories(monkeypatch) -> None:
    _mock_records(monkeypatch)
    resp = client.get("/api/scope1/inventories/inv1/data-quality?ar_version=AR5", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    tiers = {r["tier"] for r in body["rows"]}
    assert tiers == {1, 4, 5}                          # combustion T1 + fugitive T4 + process T5
    assert body["total_count"] == 3
    # shares sum to ~100
    assert abs(sum(r["pct"] for r in body["rows"]) - 100.0) < 0.01
    t1 = next(r for r in body["rows"] if r["tier"] == 1)
    assert t1["label"] == "Measured (CEMS/meter)"


# --- Member emails ----------------------------------------------------------

def test_members_route_attaches_emails(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_member_roles", lambda **k: [
        {"user_id": "u1", "role": "admin", "explicit": True},
        {"user_id": "u2", "role": "editor", "explicit": False}])
    monkeypatch.setattr("db.scope1_store.resolve_member_emails",
                        lambda ids: {"u1": "alice@co.com"})     # u2 unresolved
    resp = client.get("/api/scope1/members", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    members = {m["user_id"]: m for m in resp.json()["members"]}
    assert members["u1"]["email"] == "alice@co.com"
    assert members["u2"]["email"] is None                       # falls back to id in UI


def test_members_route_survives_email_resolution_failure(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_member_roles", lambda **k: [
        {"user_id": "u1", "role": "admin", "explicit": True}])

    def _boom(ids):
        raise RuntimeError("admin api down")
    monkeypatch.setattr("db.scope1_store.resolve_member_emails", _boom)
    resp = client.get("/api/scope1/members", headers=AUTH_HEADERS)
    assert resp.status_code == 200                              # best-effort, no 500
    assert resp.json()["members"][0]["email"] is None
