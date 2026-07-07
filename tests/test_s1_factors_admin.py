"""Tests for admin emission-factor overrides + DB-backed loader (#5, PRD C1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import CurrentUser
from api.routes.scope1 import _library
from s1_factors import EmissionFactorLibrary, rows_to_factors
from s1_factors.models import RANK_SUPPLIER
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


def _override_row(**kw):
    base = {
        "id": "ov1", "fuel_or_activity": "natural_gas",
        "source_category": "stationary_combustion", "gas": "CO2",
        "value": 50.0, "unit": "kg/mmBtu", "source": "Supplier attestation",
        "source_version": "2026-01", "region": "US", "basis": "supplier",
        "valid_to": None, "model_year": None,
    }
    base.update(kw)
    return base


@pytest.fixture(autouse=True)
def _admin_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "admin")


# --- Pure library layering --------------------------------------------------

def test_override_replaces_global_factor() -> None:
    lib = EmissionFactorLibrary.with_overrides(rows_to_factors([_override_row()]))
    ef = lib.select("natural_gas", "stationary_combustion", "CO2")
    assert ef.value == 50.0  # override wins over EPA 53.06
    assert ef.source == "Supplier attestation"


def test_no_overrides_is_byte_identical_to_default() -> None:
    lib = EmissionFactorLibrary.with_overrides([])
    ef = lib.select("natural_gas", "stationary_combustion", "CO2")
    assert ef.value == 53.06  # untouched EPA canonical value


def test_rows_to_factors_filters_retired_and_maps_basis() -> None:
    rows = [_override_row(), _override_row(id="old", valid_to="2025-01-01")]
    factors = rows_to_factors(rows)
    assert len(factors) == 1  # retired row dropped
    assert factors[0].selection_rank == RANK_SUPPLIER  # basis -> rank


def test_override_only_affects_its_key() -> None:
    lib = EmissionFactorLibrary.with_overrides(rows_to_factors([_override_row()]))
    # diesel is untouched
    ef = lib.select("diesel_no2", "stationary_combustion", "CO2")
    assert ef.value == 73.96


# --- DB-backed loader -------------------------------------------------------

def test_library_loader_uses_org_overrides(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_ef_overrides", lambda **k: [_override_row()])
    user = CurrentUser(user_id="u1", access_token="t")
    ef = _library(user).select("natural_gas", "stationary_combustion", "CO2")
    assert ef.value == 50.0


def test_library_loader_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_ef_overrides", lambda **k: [])
    user = CurrentUser(user_id="u1", access_token="t")
    ef = _library(user).select("natural_gas", "stationary_combustion", "CO2")
    assert ef.value == 53.06


# --- Routes -----------------------------------------------------------------

def test_list_factors_merges_and_flags(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_ef_overrides", lambda **k: [_override_row()])
    resp = client.get("/api/scope1/factors", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["your_role"] == "admin"
    assert body["override_count"] == 1
    ng = next(f for f in body["factors"]
              if f["fuel_or_activity"] == "natural_gas" and f["gas"] == "CO2"
              and f["source_category"] == "stationary_combustion")
    assert ng["is_override"] and ng["value"] == 50.0
    # exactly one natural_gas/stationary/CO2 row (global replaced, not duplicated)
    dupes = [f for f in body["factors"]
             if f["fuel_or_activity"] == "natural_gas" and f["gas"] == "CO2"
             and f["source_category"] == "stationary_combustion"]
    assert len(dupes) == 1


def test_create_override_versions_existing(monkeypatch) -> None:
    calls = {"retired": [], "created": []}
    monkeypatch.setattr("db.scope1_store.find_active_ef_override",
                        lambda data, **k: {"id": "old"})
    monkeypatch.setattr("db.scope1_store.retire_ef_override",
                        lambda oid, vt, **k: calls["retired"].append(oid) or {"id": oid})
    monkeypatch.setattr("db.scope1_store.create_ef_override",
                        lambda data, **k: calls["created"].append(data) or {"id": "new", **data})
    resp = client.post("/api/scope1/factors/override", headers=AUTH_HEADERS, json={
        "fuel_or_activity": "natural_gas", "source_category": "stationary_combustion",
        "gas": "CO2", "value": 52.0, "unit": "kg/mmBtu",
        "source": "EPA EF Hub", "source_version": "2026-01", "basis": "custom",
    })
    assert resp.status_code == 200
    assert calls["retired"] == ["old"]  # superseded old active override
    assert calls["created"][0]["value"] == 52.0


def test_create_override_requires_admin(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")
    resp = client.post("/api/scope1/factors/override", headers=AUTH_HEADERS, json={
        "fuel_or_activity": "natural_gas", "source_category": "stationary_combustion",
        "gas": "CO2", "value": 52.0, "unit": "kg/mmBtu",
        "source": "x", "source_version": "y",
    })
    assert resp.status_code == 403


def test_retire_override_404_when_missing(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.retire_ef_override", lambda oid, vt, **k: None)
    resp = client.delete("/api/scope1/factors/override/nope", headers=AUTH_HEADERS)
    assert resp.status_code == 404
