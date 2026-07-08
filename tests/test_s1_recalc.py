"""Tests for the base-year recalculation engine (GHG Protocol Ch. 5)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from s1_recalc import RecalcEvent, analyze_recalc, is_structural
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def _editor_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")


# --- Pure engine ------------------------------------------------------------

def test_structural_classification() -> None:
    assert is_structural("acquisition")
    assert is_structural("methodology_change")
    assert not is_structural("organic_growth")


def test_organic_change_never_recalculated() -> None:
    a = analyze_recalc(
        base_year=2020, base_year_total_tco2e=1000.0, significance_threshold_pct=5.0,
        events=[RecalcEvent("e1", "organic_growth", "new plant", 300.0)],
    )
    assert a.structural_delta_pending == 0.0
    assert a.organic_delta == 300.0
    assert a.restated_total == 1000.0  # unchanged
    assert a.recalc_required is False  # 0% impact < 5%
    assert not a.has_pending


def test_acquisition_triggers_recalc_over_threshold() -> None:
    a = analyze_recalc(
        base_year=2020, base_year_total_tco2e=1000.0, significance_threshold_pct=5.0,
        events=[RecalcEvent("e1", "acquisition", "bought Co", 80.0)],
    )
    assert a.structural_delta_pending == 80.0
    assert a.restated_total == 1080.0
    assert a.pct_impact == 8.0
    assert a.recalc_required is True
    assert a.has_pending


def test_divestiture_is_negative() -> None:
    a = analyze_recalc(
        base_year=2020, base_year_total_tco2e=1000.0, significance_threshold_pct=5.0,
        events=[RecalcEvent("e1", "divestiture", "sold unit", -120.0)],
    )
    assert a.restated_total == 880.0
    assert a.pct_impact == 12.0
    assert a.recalc_required is True


def test_applied_events_excluded_from_pending() -> None:
    a = analyze_recalc(
        base_year=2020, base_year_total_tco2e=1080.0, significance_threshold_pct=5.0,
        events=[
            RecalcEvent("e1", "acquisition", "done", 80.0, applied=True),
            RecalcEvent("e2", "acquisition", "new", 20.0, applied=False),
        ],
    )
    assert a.structural_delta_pending == 20.0  # only the un-applied one
    assert a.restated_total == 1100.0


def test_threshold_undeclared_is_undecidable() -> None:
    a = analyze_recalc(
        base_year=2020, base_year_total_tco2e=1000.0, significance_threshold_pct=None,
        events=[RecalcEvent("e1", "acquisition", "x", 80.0)],
    )
    assert a.recalc_required is None  # can't decide without a policy threshold


def test_zero_base_total_no_divide_by_zero() -> None:
    a = analyze_recalc(
        base_year=2020, base_year_total_tco2e=0.0, significance_threshold_pct=5.0,
        events=[RecalcEvent("e1", "acquisition", "x", 50.0)],
    )
    assert a.pct_impact is None
    assert a.restated_total == 50.0


# --- Routes -----------------------------------------------------------------

_INV = {"id": "inv1", "base_year": 2020, "base_year_total_tco2e": "1000",
        "significance_threshold_pct": "5"}


def test_add_event_returns_analysis(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_inventory", lambda i, **k: dict(_INV))
    monkeypatch.setattr("db.scope1_store.create_recalc_event", lambda d, **k: {"id": "e1", **d})
    monkeypatch.setattr("db.scope1_store.list_recalc_events", lambda i, **k: [
        {"id": "e1", "trigger_type": "acquisition", "description": "x",
         "delta_tco2e": "80", "applied": False},
    ])
    resp = client.post("/api/scope1/inventories/inv1/recalc/events", headers=AUTH_HEADERS,
                       json={"trigger_type": "acquisition", "delta_tco2e": 80})
    assert resp.status_code == 200
    body = resp.json()
    assert body["restated_total"] == 1080.0
    assert body["recalc_required"] is True
    assert body["events"][0]["is_structural"] is True


def test_apply_folds_pending_and_marks_applied(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_inventory", lambda i, **k: dict(_INV))
    monkeypatch.setattr("db.scope1_store.list_recalc_events", lambda i, **k: [
        {"id": "e1", "trigger_type": "acquisition", "delta_tco2e": "80", "applied": False},
    ])
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.set_base_year",
                        lambda inv, patch, **k: captured.update(patch) or {"id": inv, **patch})
    monkeypatch.setattr("db.scope1_store.mark_recalc_events_applied",
                        lambda ids, at, **k: captured.update(applied_ids=ids) or [])
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post("/api/scope1/inventories/inv1/recalc/apply", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert captured["base_year_total_tco2e"] == 1080.0  # restated total persisted
    assert captured["applied_ids"] == ["e1"]


def test_apply_with_no_pending_400(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_inventory", lambda i, **k: dict(_INV))
    monkeypatch.setattr("db.scope1_store.list_recalc_events", lambda i, **k: [])
    resp = client.post("/api/scope1/inventories/inv1/recalc/apply", headers=AUTH_HEADERS)
    assert resp.status_code == 400


def test_delete_event_404_when_applied(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_inventory", lambda i, **k: dict(_INV))
    monkeypatch.setattr("db.scope1_store.delete_recalc_event", lambda e, **k: None)
    resp = client.delete("/api/scope1/inventories/inv1/recalc/events/e1", headers=AUTH_HEADERS)
    assert resp.status_code == 404


def test_add_event_requires_editor(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "viewer")
    resp = client.post("/api/scope1/inventories/inv1/recalc/events", headers=AUTH_HEADERS,
                       json={"trigger_type": "acquisition", "delta_tco2e": 80})
    assert resp.status_code == 403
