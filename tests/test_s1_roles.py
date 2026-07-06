"""Tests for Scope 1 users & roles (admin/editor/viewer, app-layer enforcement)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import AUTH_HEADERS, TEST_USER_ID

client = TestClient(app)

_ENTITY = {"name": "E", "jurisdiction": "US", "entity_type": "parent", "effective_from": "2025-01-01"}


def _role(monkeypatch, role: str) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: role)


# --- Default resolution (pure) ----------------------------------------------

def test_default_role_mapping() -> None:
    from db.scope1_store import _default_role
    assert _default_role("admin") == "admin"
    assert _default_role("member") == "editor"
    assert _default_role("demo_member") == "editor"


# --- Write gating -----------------------------------------------------------

def test_viewer_blocked_from_write(monkeypatch) -> None:
    _role(monkeypatch, "viewer")
    resp = client.post("/api/scope1/entities", json=_ENTITY, headers=AUTH_HEADERS)
    assert resp.status_code == 403
    assert "viewer" in resp.json()["detail"]


def test_editor_can_write(monkeypatch) -> None:
    _role(monkeypatch, "editor")
    monkeypatch.setattr("db.scope1_store.create_entity", lambda data, **k: {"id": "e1", **data})
    resp = client.post("/api/scope1/entities", json=_ENTITY, headers=AUTH_HEADERS)
    assert resp.status_code == 200


def test_viewer_can_read(monkeypatch) -> None:
    _role(monkeypatch, "viewer")
    monkeypatch.setattr("db.scope1_store.list_entities", lambda **k: [])
    resp = client.get("/api/scope1/entities", headers=AUTH_HEADERS)
    assert resp.status_code == 200


# --- Role management (admin-only) -------------------------------------------

def test_editor_cannot_manage_roles(monkeypatch) -> None:
    _role(monkeypatch, "editor")
    resp = client.post("/api/scope1/members/u2/role", json={"role": "viewer"}, headers=AUTH_HEADERS)
    assert resp.status_code == 403


def test_admin_can_set_role(monkeypatch) -> None:
    _role(monkeypatch, "admin")
    captured: dict = {}
    monkeypatch.setattr(
        "db.scope1_store.set_member_role",
        lambda uid, role, **k: captured.update(uid=uid, role=role) or {"user_id": uid, "role": role},
    )
    resp = client.post("/api/scope1/members/u2/role", json={"role": "viewer"}, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert captured == {"uid": "u2", "role": "viewer"}


def test_set_role_rejects_invalid_role(monkeypatch) -> None:
    _role(monkeypatch, "admin")
    resp = client.post("/api/scope1/members/u2/role", json={"role": "superuser"}, headers=AUTH_HEADERS)
    assert resp.status_code == 422


def test_list_members_includes_your_role_and_is_you(monkeypatch) -> None:
    _role(monkeypatch, "admin")
    monkeypatch.setattr("db.scope1_store.list_member_roles", lambda **k: [
        {"user_id": TEST_USER_ID, "role": "admin", "explicit": False},
        {"user_id": "u2", "role": "editor", "explicit": False},
    ])
    resp = client.get("/api/scope1/members", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["your_role"] == "admin"
    me = next(m for m in body["members"] if m["is_you"])
    assert me["user_id"] == TEST_USER_ID


def test_invite_adds_to_org_then_sets_role(monkeypatch) -> None:
    _role(monkeypatch, "admin")
    monkeypatch.setattr("db.org_store.find_user_id_by_email", lambda email: "u3")
    monkeypatch.setattr("db.org_store.get_active_org",
                        lambda tok, *, user_id=None: type("Org", (), {"id": "org1"})())
    monkeypatch.setattr("db.org_store.add_member", lambda uid, oid, **k: None)
    captured: dict = {}
    monkeypatch.setattr(
        "db.scope1_store.set_member_role",
        lambda uid, role, **k: captured.update(uid=uid, role=role) or {"user_id": uid, "role": role},
    )
    resp = client.post("/api/scope1/members/invite",
                       json={"email": "a@b.com", "role": "editor"}, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert captured == {"uid": "u3", "role": "editor"}
