"""Tests for process emissions (Scope 1 coverage: combustion + fugitive + process)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from s1_process import compute_emission_kg, get_process_factor, process_tco2e
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def _editor_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")


# --- Pure engine ------------------------------------------------------------

def test_compute_emission_kg() -> None:
    assert compute_emission_kg(1000, 510.0) == 510_000.0  # cement 1000 t x 510 kg/t


def test_negative_inputs_raise() -> None:
    with pytest.raises(ValueError):
        compute_emission_kg(-1, 510)


def test_co2_tco2e_is_ar_invariant() -> None:
    kg = compute_emission_kg(10_000, 510.0)  # cement CO2
    assert process_tco2e(kg, "Carbon dioxide", "AR5") == process_tco2e(kg, "Carbon dioxide", "AR6")
    assert process_tco2e(kg, "Carbon dioxide", "AR5") == 5100.0


def test_n2o_tco2e_tracks_ar_version() -> None:
    kg = compute_emission_kg(1000, 9.0)  # nitric acid N2O
    ar5 = process_tco2e(kg, "Nitrous oxide", "AR5")  # 265
    ar6 = process_tco2e(kg, "Nitrous oxide", "AR6")  # 273
    assert ar5 == 2385.0
    assert ar6 == 2457.0
    assert ar6 > ar5


def test_library_lookup() -> None:
    f = get_process_factor("nitric_acid")
    assert f["gas"] == "Nitrous oxide"
    assert f["value"] == 9.0


# --- Routes -----------------------------------------------------------------

def test_process_factors_endpoint() -> None:
    resp = client.get("/api/scope1/process-factors", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    types = {r["process_type"] for r in resp.json()}
    assert "cement_clinker" in types and "nitric_acid" in types


def test_create_process_stores_mass_not_co2e(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.create_process_record",
                        lambda row, **k: captured.update(row) or {"id": "p1", **row})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post("/api/scope1/process", headers=AUTH_HEADERS, json={
        "inventory_id": "inv1", "process_type": "cement_clinker",
        "gas_species": "Carbon dioxide", "activity_quantity": 1000, "ef_value": 510,
    })
    assert resp.status_code == 200
    assert captured["emission_kg"] == 510_000.0  # server-computed
    assert "tco2e" not in captured                # mass stored, never CO2e


def test_create_process_rejects_bad_gas() -> None:
    resp = client.post("/api/scope1/process", headers=AUTH_HEADERS, json={
        "inventory_id": "inv1", "process_type": "custom",
        "gas_species": "Ozone", "activity_quantity": 1, "ef_value": 1,
    })
    assert resp.status_code == 422


def test_list_process_derives_tco2e(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_process_records", lambda i, **k: [
        {"id": "p1", "process_type": "nitric_acid", "gas_species": "Nitrous oxide",
         "activity_quantity": "1000", "ef_value": "9", "emission_kg": "9000"},
    ])
    ar5 = client.get("/api/scope1/inventories/inv1/process?ar_version=AR5", headers=AUTH_HEADERS).json()
    ar6 = client.get("/api/scope1/inventories/inv1/process?ar_version=AR6", headers=AUTH_HEADERS).json()
    assert ar5["total_tco2e"] == 2385.0
    assert ar6["total_tco2e"] == 2457.0


def test_create_process_requires_editor(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "viewer")
    resp = client.post("/api/scope1/process", headers=AUTH_HEADERS, json={
        "inventory_id": "inv1", "process_type": "cement_clinker",
        "gas_species": "Carbon dioxide", "activity_quantity": 1000, "ef_value": 510,
    })
    assert resp.status_code == 403
