"""Tests for the guided-setup onboarding wizard (MVP gap #4, PRD P1)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from s1_onboarding import OnboardingCounts, build_onboarding
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


# --- Pure checklist logic ---------------------------------------------------

def test_empty_org_all_todo() -> None:
    cl = build_onboarding(OnboardingCounts())
    assert cl.total == 6
    assert cl.complete == 0
    assert cl.pct == 0.0
    assert cl.next_key == "entity"
    assert all(not s.done for s in cl.steps)


def test_partial_progress_next_is_first_incomplete() -> None:
    cl = build_onboarding(OnboardingCounts(entities=2, facilities=1))
    assert cl.complete == 2
    assert cl.next_key == "source"
    done = {s.key: s.done for s in cl.steps}
    assert done["entity"] and done["facility"]
    assert not done["source"]


def test_source_uses_in_scope_count() -> None:
    # count is threaded straight through from the route (non-excluded sources).
    cl = build_onboarding(OnboardingCounts(sources=3))
    src = next(s for s in cl.steps if s.key == "source")
    assert src.done and src.count == 3


def test_fully_complete() -> None:
    cl = build_onboarding(
        OnboardingCounts(
            entities=1, facilities=1, sources=1,
            inventories=1, records=5, locked_inventories=1,
        )
    )
    assert cl.is_complete
    assert cl.complete == cl.total == 6
    assert cl.pct == 100.0
    assert cl.next_key is None


def test_data_step_needs_records_disclose_needs_lock() -> None:
    cl = build_onboarding(
        OnboardingCounts(entities=1, facilities=1, sources=1, inventories=1)
    )
    done = {s.key: s.done for s in cl.steps}
    assert done["inventory"]
    assert not done["data"]  # no records yet
    assert not done["disclose"]  # nothing locked
    assert cl.next_key == "data"


# --- Route ------------------------------------------------------------------

def test_onboarding_route(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_entities", lambda **k: [{"id": "e1"}])
    monkeypatch.setattr("db.scope1_store.list_facilities", lambda **k: [{"id": "f1"}])
    monkeypatch.setattr(
        "db.scope1_store.list_sources",
        lambda **k: [{"id": "s1"}, {"id": "s2", "is_excluded": True}],
    )
    monkeypatch.setattr(
        "db.scope1_store.list_inventories",
        lambda **k: [{"id": "inv1", "locked": True}],
    )
    monkeypatch.setattr(
        "db.scope1_store.list_records_for_inventory",
        lambda inv, **k: [{"id": "r1"}, {"id": "r2"}],
    )
    resp = client.get("/api/scope1/onboarding", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 6
    assert body["complete"] == 6  # all steps satisfied
    assert body["next_key"] is None
    src = next(s for s in body["steps"] if s["key"] == "source")
    assert src["count"] == 1  # excluded source not counted


def test_onboarding_route_partial(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_entities", lambda **k: [{"id": "e1"}])
    monkeypatch.setattr("db.scope1_store.list_facilities", lambda **k: [])
    monkeypatch.setattr("db.scope1_store.list_sources", lambda **k: [])
    monkeypatch.setattr("db.scope1_store.list_inventories", lambda **k: [])
    resp = client.get("/api/scope1/onboarding", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["complete"] == 1
    assert body["next_key"] == "facility"
