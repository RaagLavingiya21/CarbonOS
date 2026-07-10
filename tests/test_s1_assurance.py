"""Tests for the assurance & verification workflow."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def _editor_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")


def test_set_assurance_route(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.set_assurance",
                        lambda inv, patch, **k: captured.update(inv=inv, **patch) or {"id": inv, **patch})
    monkeypatch.setattr("db.scope1_store.get_assurance_statement", lambda inv, **k: None)
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post("/api/scope1/inventories/inv1/assurance", headers=AUTH_HEADERS,
                       json={"assurance_level": "limited", "assurance_standard": "ISAE_3410"})
    assert resp.status_code == 200
    assert captured["assurance_level"] == "limited"
    assert captured["assurance_standard"] == "ISAE_3410"
    body = resp.json()
    assert body["assurance_level"] == "limited"
    assert body["statement_on_file"] is False


def test_set_assurance_rejects_bad_level() -> None:
    resp = client.post("/api/scope1/inventories/inv1/assurance", headers=AUTH_HEADERS,
                       json={"assurance_level": "audited"})       # not in enum
    assert resp.status_code == 422


def test_set_assurance_rejects_bad_standard() -> None:
    resp = client.post("/api/scope1/inventories/inv1/assurance", headers=AUTH_HEADERS,
                       json={"assurance_level": "limited", "assurance_standard": "SOX"})
    assert resp.status_code == 422


def test_upload_assurance_statement_keeps_evidence(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.upload_evidence",
                        lambda data, **k: captured.update(k) or {"id": "ev1"})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post(
        "/api/scope1/inventories/inv1/assurance/statement",
        files={"file": ("assurance.pdf", b"%PDF-1.4 fake", "application/pdf")},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["evidence_document_id"] == "ev1"
    assert captured["document_type"] == "assurance_statement"     # tagged correctly


def test_get_assurance_status_reports_statement(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_inventory",
                        lambda inv, **k: {"id": inv, "assurance_level": "reasonable",
                                          "assurance_standard": "ISO_14064-3"})
    monkeypatch.setattr("db.scope1_store.get_assurance_statement",
                        lambda inv, **k: {"id": "ev9"})
    resp = client.get("/api/scope1/inventories/inv1/assurance", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["assurance_level"] == "reasonable"
    assert body["statement_on_file"] is True and body["statement_id"] == "ev9"


def test_viewer_blocked(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "viewer")
    resp = client.post("/api/scope1/inventories/inv1/assurance", headers=AUTH_HEADERS,
                       json={"assurance_level": "limited"})
    assert resp.status_code == 403
