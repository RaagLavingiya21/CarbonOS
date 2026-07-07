"""Tests for incumbent / prior-year base-year import (A1b)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from s1_intake import parse_base_year_csv
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def _editor_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")


# --- Parser (pure) ----------------------------------------------------------

def test_parse_valid() -> None:
    r = parse_base_year_csv(b"base_year,total_tco2e,gwp_version\n2023,487.31,AR6\n")
    assert r.is_valid
    assert r.base_year == 2023
    assert r.total_tco2e == 487.31
    assert r.gwp_version == "AR6"


def test_parse_missing_columns() -> None:
    r = parse_base_year_csv(b"year,total\n2023,10\n")
    assert not r.is_valid
    assert any("Missing" in e for e in r.errors)


def test_parse_bad_values() -> None:
    r = parse_base_year_csv(b"base_year,total_tco2e\nabc,-5\n")
    assert not r.is_valid


def test_parse_gwp_defaults_ar5() -> None:
    r = parse_base_year_csv(b"base_year,total_tco2e\n2023,100\n")
    assert r.is_valid and r.gwp_version == "AR5"


# --- Routes -----------------------------------------------------------------

def test_set_base_year_route(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.set_base_year",
                        lambda inv, patch, **k: captured.update(inv=inv, **patch) or {"id": inv, **patch})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post("/api/scope1/inventories/inv1/base-year",
                       json={"base_year": 2023, "base_year_total_tco2e": 487.31}, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert captured["base_year"] == 2023
    assert captured["base_year_total_tco2e"] == 487.31
    assert captured["base_year_gwp_version"] == "AR5"


def test_import_base_year_route(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.upload_evidence", lambda data, **k: {"id": "ev1"})
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.set_base_year",
                        lambda inv, patch, **k: captured.update(patch) or {"id": inv, **patch})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post(
        "/api/scope1/inventories/inv1/base-year/import",
        files={"file": ("prior.csv", b"base_year,total_tco2e,gwp_version\n2023,487.31,AR5\n", "text/csv")},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["evidence_document_id"] == "ev1"                 # source doc kept as evidence
    assert body["imported"]["base_year"] == 2023
    assert captured["base_year_total_tco2e"] == 487.31


def test_import_rejects_invalid_csv(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.upload_evidence", lambda data, **k: {"id": "ev1"})
    resp = client.post(
        "/api/scope1/inventories/inv1/base-year/import",
        files={"file": ("x.csv", b"foo,bar\n1,2\n", "text/csv")}, headers=AUTH_HEADERS,
    )
    assert resp.status_code == 422


def test_viewer_blocked(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "viewer")
    resp = client.post("/api/scope1/inventories/inv1/base-year",
                       json={"base_year": 2023, "base_year_total_tco2e": 10}, headers=AUTH_HEADERS)
    assert resp.status_code == 403
