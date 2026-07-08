"""Tests for year-over-year trends + emissions intensity (post-MVP depth)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from s1_reporting import InventoryDatum, build_trends
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


@pytest.fixture(autouse=True)
def _editor_role(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "editor")


# --- Pure trend logic -------------------------------------------------------

def test_yoy_and_ordering() -> None:
    data = [
        InventoryDatum("i2", 2024, 120.0),
        InventoryDatum("i1", 2023, 100.0),
    ]
    r = build_trends(data, ar_version="AR5")
    assert [p.reporting_year for p in r.points] == [2023, 2024]  # sorted ascending
    assert r.points[0].yoy_abs is None  # first year has no prior
    assert r.points[1].yoy_abs == 20.0
    assert r.points[1].yoy_pct == 20.0


def test_intensity_metrics() -> None:
    data = [InventoryDatum(
        "i1", 2023, 500.0,
        annual_revenue=250_000_000.0, output_quantity=1000.0,
        output_unit="tonnes", headcount=200,
    )]
    p = build_trends(data, ar_version="AR5").points[0]
    assert p.per_revenue_mm == 2.0    # 500 tCO2e / $250M
    assert p.per_output == 0.5         # 500 / 1000 tonnes
    assert p.output_unit == "tonnes"
    assert p.per_headcount == 2.5      # 500 / 200 FTE


def test_intensity_none_when_denominator_missing_or_zero() -> None:
    p = build_trends(
        [InventoryDatum("i1", 2023, 500.0, annual_revenue=0.0, headcount=0)],
        ar_version="AR5",
    ).points[0]
    assert p.per_revenue_mm is None
    assert p.per_output is None
    assert p.per_headcount is None


def test_base_year_comparison() -> None:
    data = [InventoryDatum("i1", 2024, 80.0)]
    r = build_trends(data, ar_version="AR5", base_year=2020, base_year_total_tco2e=100.0)
    assert r.latest_vs_base_abs == -20.0
    assert r.latest_vs_base_pct == -20.0


def test_base_year_flag() -> None:
    data = [InventoryDatum("i1", 2020, 100.0), InventoryDatum("i2", 2024, 80.0)]
    r = build_trends(data, ar_version="AR5", base_year=2020, base_year_total_tco2e=100.0)
    assert r.points[0].is_base_year is True
    assert r.points[1].is_base_year is False


def test_empty() -> None:
    r = build_trends([], ar_version="AR6")
    assert r.points == []
    assert r.latest_vs_base_abs is None


# --- Routes -----------------------------------------------------------------

def test_trends_route(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.list_inventories", lambda **k: [
        {"id": "i1", "reporting_year": 2023, "annual_revenue": "100000000",
         "base_year": 2023, "base_year_total_tco2e": "90"},
        {"id": "i2", "reporting_year": 2024, "annual_revenue": "120000000",
         "base_year": 2023, "base_year_total_tco2e": "90"},
    ])

    class _Rep:
        def __init__(self, t): self.total_scope1_tco2e = t

    totals = {"i1": 100.0, "i2": 110.0}
    monkeypatch.setattr("api.routes.scope1._assemble_report",
                        lambda inv_id, ar, user: _Rep(totals[inv_id]))
    resp = client.get("/api/scope1/trends?ar_version=AR5", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert [p["reporting_year"] for p in body["points"]] == [2023, 2024]
    assert body["points"][1]["yoy_abs"] == 10.0
    assert body["points"][0]["per_revenue_mm"] == 1.0  # 100 / $100M
    # latest (110) vs base-year total (90)
    assert body["base_year"] == 2023
    assert round(body["latest_vs_base_pct"], 4) == round((110 - 90) / 90 * 100, 4)


def test_set_metrics_route(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.set_inventory_metrics",
                        lambda inv, patch, **k: captured.update(patch) or {"id": inv, **patch})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post("/api/scope1/inventories/i1/metrics", headers=AUTH_HEADERS,
                       json={"annual_revenue": 5000000, "headcount": 50})
    assert resp.status_code == 200
    assert captured["annual_revenue"] == 5000000
    assert captured["headcount"] == 50


def test_set_metrics_rejects_empty(monkeypatch) -> None:
    resp = client.post("/api/scope1/inventories/i1/metrics", headers=AUTH_HEADERS, json={})
    assert resp.status_code == 422


def test_set_metrics_requires_editor(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.get_scope1_role", lambda **k: "viewer")
    resp = client.post("/api/scope1/inventories/i1/metrics", headers=AUTH_HEADERS,
                       json={"headcount": 10})
    assert resp.status_code == 403
