"""Tests for fugitive / refrigerant emissions (Scope 1 coverage beyond combustion)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from s1_fugitive import (
    UnknownRefrigerant,
    compute_leaked_kg,
    fugitive_tco2e,
    refrigerant_gwp,
)
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def _editor_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")


# --- Pure engine ------------------------------------------------------------

def test_screening_method() -> None:
    assert compute_leaked_kg("screening", charge_kg=200, leak_rate_pct=12.5) == 25.0


def test_material_balance_method() -> None:
    # purchases + beginning - ending
    assert compute_leaked_kg(
        "material_balance", purchases_kg=50, beginning_inventory_kg=200, ending_inventory_kg=230
    ) == 20.0


def test_material_balance_clamped_at_zero() -> None:
    assert compute_leaked_kg(
        "material_balance", purchases_kg=0, beginning_inventory_kg=100, ending_inventory_kg=150
    ) == 0.0


def test_screening_requires_inputs() -> None:
    with pytest.raises(ValueError):
        compute_leaked_kg("screening", charge_kg=100)  # missing leak_rate_pct


def test_blend_gwp_is_mass_weighted() -> None:
    # R-410A = 50% R-32 + 50% R-125 at AR5 (677, 3170)
    assert refrigerant_gwp("R-410A", "AR5") == 0.5 * 677 + 0.5 * 3170


def test_ar_version_changes_tco2e() -> None:
    ar5 = fugitive_tco2e(10.0, "R-134a", "AR5")   # 1300
    ar6 = fugitive_tco2e(10.0, "R-134a", "AR6")   # 1526
    assert ar5 == 13.0
    assert ar6 == 15.26
    assert ar6 > ar5


def test_unknown_refrigerant_raises() -> None:
    with pytest.raises(UnknownRefrigerant):
        refrigerant_gwp("R-999xyz", "AR5")


# --- Routes -----------------------------------------------------------------

def test_refrigerants_endpoint() -> None:
    resp = client.get("/api/scope1/refrigerants", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert "R-410A" in names and "R-134a" in names


def test_create_fugitive_computes_and_stores_mass(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.create_fugitive_record",
                        lambda row, **k: captured.update(row) or {"id": "f1", **row})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post("/api/scope1/fugitive", headers=AUTH_HEADERS, json={
        "inventory_id": "inv1", "refrigerant": "R-410A", "method": "screening",
        "charge_kg": 100, "leak_rate_pct": 10,
    })
    assert resp.status_code == 200
    assert captured["leaked_kg"] == 10.0     # 100 x 10% computed server-side
    assert "tco2e" not in captured           # mass stored, never CO2e


def test_create_fugitive_rejects_unknown_refrigerant() -> None:
    resp = client.post("/api/scope1/fugitive", headers=AUTH_HEADERS, json={
        "inventory_id": "inv1", "refrigerant": "R-nope", "method": "screening",
        "charge_kg": 100, "leak_rate_pct": 10,
    })
    assert resp.status_code == 422


def test_list_fugitive_derives_tco2e_at_ar_version(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_fugitive_records", lambda i, **k: [
        {"id": "f1", "refrigerant": "R-134a", "method": "screening", "leaked_kg": "10"},
    ])
    ar5 = client.get("/api/scope1/inventories/inv1/fugitive?ar_version=AR5", headers=AUTH_HEADERS).json()
    ar6 = client.get("/api/scope1/inventories/inv1/fugitive?ar_version=AR6", headers=AUTH_HEADERS).json()
    assert ar5["total_tco2e"] == 13.0
    assert ar6["total_tco2e"] == 15.26
    assert ar5["records"][0]["gwp"] == 1300


def test_create_fugitive_requires_editor(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "viewer")
    resp = client.post("/api/scope1/fugitive", headers=AUTH_HEADERS, json={
        "inventory_id": "inv1", "refrigerant": "R-410A", "method": "screening",
        "charge_kg": 100, "leak_rate_pct": 10,
    })
    assert resp.status_code == 403
