"""Tests for the Bayou credential-connect routes (V2 Priority 2 completion).

Covers the wired API surface + the security posture: the API key is never
returned to the client, writes are admin-gated, and the backend uses a
service-role client (mocked here) so credentials never flow through the anon key.
"""

from __future__ import annotations

import types

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db.s1_bayou_store import NoCredentialsError
from tests.conftest import AUTH_HEADERS

client = TestClient(app)

_ROW = {
    "id": "cred1", "org_id": "org123", "bayou_api_key": "secret_key",
    "is_active": True, "last_sync": None, "next_sync": None,
    "created_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture(autouse=True)
def _admin_and_org(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "admin")
    monkeypatch.setattr("db.org_store.get_active_org",
                        lambda *a, **k: types.SimpleNamespace(id="org123"))
    monkeypatch.setattr("api.routes.scope1.get_service_client", lambda: object())


def test_get_status_never_returns_key(monkeypatch) -> None:
    monkeypatch.setattr("db.s1_bayou_store.get_or_create_credentials",
                        lambda org, c, **k: dict(_ROW))
    resp = client.get("/api/scope1/bayou-credentials", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is True
    assert body["configured"] is True
    assert "bayou_api_key" not in body  # secret never surfaced


def test_set_key_admin(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("db.s1_bayou_store.get_or_create_credentials",
                        lambda org, c, **k: dict(_ROW))
    monkeypatch.setattr("db.s1_bayou_store.set_api_key",
                        lambda org, key, c, **k: captured.update(key=key) or {**_ROW, "is_active": True})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post("/api/scope1/bayou-credentials", headers=AUTH_HEADERS,
                       json={"bayou_api_key": "live_abc"})
    assert resp.status_code == 200
    assert captured["key"] == "live_abc"
    assert "bayou_api_key" not in resp.json()


def test_set_key_requires_admin(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")
    resp = client.post("/api/scope1/bayou-credentials", headers=AUTH_HEADERS,
                       json={"bayou_api_key": "live_abc"})
    assert resp.status_code == 403


def test_disconnect_admin(monkeypatch) -> None:
    monkeypatch.setattr("db.s1_bayou_store.deactivate_credentials",
                        lambda org, c, **k: {**_ROW, "is_active": False})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.delete("/api/scope1/bayou-credentials", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


def test_disconnect_404_when_missing(monkeypatch) -> None:
    def _raise(*a, **k):
        raise NoCredentialsError("none")
    monkeypatch.setattr("db.s1_bayou_store.deactivate_credentials", _raise)
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.delete("/api/scope1/bayou-credentials", headers=AUTH_HEADERS)
    assert resp.status_code == 404


def _pull_result(bill_ids: list[str]):
    """A fake PullResult whose parsed items expose .bill.bill_id + .extraction."""
    from s1_intake.bayou import PullResult
    parsed = [
        types.SimpleNamespace(
            bill=types.SimpleNamespace(bill_id=bid),
            extraction=types.SimpleNamespace(to_dict=lambda: {"gas": 1}, min_confidence=0.95),
        )
        for bid in bill_ids
    ]
    return PullResult(fetched=len(bill_ids) + 1, parsed=parsed)  # +1 "still parsing" bill


def _wire_sync(monkeypatch, bill_ids: list[str], queue_seen: list[str] | None = None) -> list[dict]:
    monkeypatch.setattr("db.s1_bayou_store.get_active_api_key", lambda org, c, **k: "live_key")
    monkeypatch.setattr("api.routes.scope1.pull_parsed_extractions",
                        lambda cl: _pull_result(bill_ids))
    monkeypatch.setattr("db.scope1_store.list_inventories",
                        lambda **k: [{"id": "inv1", "reporting_year": 2024}])
    monkeypatch.setattr("db.scope1_store.list_ocr_queue",
                        lambda **k: [{"bayou_bill_id": b} for b in (queue_seen or [])])
    created: list[dict] = []
    monkeypatch.setattr("db.scope1_store.create_ocr_extraction",
                        lambda row, **k: created.append(row) or {"id": "e1", **row})
    monkeypatch.setattr("db.s1_bayou_store.mark_sync_complete",
                        lambda org, c, **k: {**_ROW, "last_sync": "2026-01-02T00:00:00Z",
                                             "next_sync": "2026-01-02T01:00:00Z"})
    return created


def test_sync_when_due_pulls_and_queues(monkeypatch) -> None:
    monkeypatch.setattr("db.s1_bayou_store.should_sync", lambda org, c, **k: True)
    created = _wire_sync(monkeypatch, ["b1", "b2"])
    resp = client.post("/api/scope1/bayou-credentials/sync", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["synced"] is True
    assert body["bills_fetched"] == 3 and body["bills_parsed"] == 2 and body["queued"] == 2
    assert {r["bayou_bill_id"] for r in created} == {"b1", "b2"}
    assert body["next_sync"] == "2026-01-02T01:00:00Z"


def test_sync_dedupes_already_queued(monkeypatch) -> None:
    monkeypatch.setattr("db.s1_bayou_store.should_sync", lambda org, c, **k: True)
    created = _wire_sync(monkeypatch, ["b1", "b2"], queue_seen=["b1"])
    resp = client.post("/api/scope1/bayou-credentials/sync", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["queued"] == 1               # b1 skipped (already queued)
    assert {r["bayou_bill_id"] for r in created} == {"b2"}


def test_sync_skipped_when_not_due(monkeypatch) -> None:
    monkeypatch.setattr("db.s1_bayou_store.should_sync", lambda org, c, **k: False)
    resp = client.post("/api/scope1/bayou-credentials/sync", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["synced"] is False


def test_sync_force_overrides_schedule(monkeypatch) -> None:
    monkeypatch.setattr("db.s1_bayou_store.should_sync", lambda org, c, **k: False)
    _wire_sync(monkeypatch, [])
    resp = client.post("/api/scope1/bayou-credentials/sync?force=true", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["synced"] is True


def test_sync_requires_editor(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "viewer")
    resp = client.post("/api/scope1/bayou-credentials/sync", headers=AUTH_HEADERS)
    assert resp.status_code == 403
