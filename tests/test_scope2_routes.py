"""Scope 2 API route tests (stores mocked; auth bypassed via conftest).

Exercises site CRUD, CSV preview, and the full run-calculation orchestration
(stores -> engine -> persisted result) without a live database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


def _site_row(**kw) -> dict:
    row = {
        "site_id": 1,
        "org_id": "org-1",
        "user_id": "u-1",
        "name": "Store 1",
        "site_type": "retail",
        "address": "1 Main St",
        "zip": "10001",
        "country": "US",
        "egrid_subregion": "TESTSUB",
        "iea_country": None,
        "ownership": "tenant_metered",
        "lease_type": "nnn",
        "franchise_flag": False,
        "scope3_cat14_note": None,
        "consolidation_approach": "operational_control",
        "status": "active",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    row.update(kw)
    return row


# --- site CRUD -------------------------------------------------------------


def test_create_site(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_sites.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr(
        "db.s2_site_store.create_site",
        lambda payload, *, org_id, user_id, access_token: 1,
    )
    monkeypatch.setattr("db.s2_site_store.get_site", lambda sid, token: _site_row())

    resp = client.post(
        "/api/scope2/sites",
        headers=AUTH_HEADERS,
        json={"name": "Store 1", "site_type": "retail"},
    )
    assert resp.status_code == 201
    assert resp.json()["site_id"] == 1
    assert resp.json()["site_type"] == "retail"


def test_list_sites(monkeypatch) -> None:
    monkeypatch.setattr("db.s2_site_store.list_sites", lambda token: [_site_row()])
    resp = client.get("/api/scope2/sites", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_site_404(monkeypatch) -> None:
    monkeypatch.setattr("db.s2_site_store.get_site", lambda sid, token: None)
    resp = client.get("/api/scope2/sites/999", headers=AUTH_HEADERS)
    assert resp.status_code == 404


def test_create_site_requires_active_org(monkeypatch) -> None:
    from fastapi import HTTPException

    def _no_org(cu):
        raise HTTPException(status_code=400, detail="No active organization")

    monkeypatch.setattr("api.routes.scope2_sites.resolve_org_id", _no_org)
    resp = client.post(
        "/api/scope2/sites",
        headers=AUTH_HEADERS,
        json={"name": "X", "site_type": "office"},
    )
    assert resp.status_code == 400


# --- CSV preview -----------------------------------------------------------


def test_csv_preview(monkeypatch) -> None:
    body = {
        "csv_text": "Store,From,To,Usage,Unit\nS1,2022-01-01,2022-01-31,1500,kWh\n",
        "mapping": {
            "site_ref": "Store",
            "period_start": "From",
            "period_end": "To",
            "quantity": "Usage",
            "unit": "Unit",
        },
    }
    resp = client.post("/api/scope2/bills/preview-csv", headers=AUTH_HEADERS, json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid_count"] == 1
    assert data["bills"][0]["canonical_mwh"] == pytest.approx(1.5)


# --- run calculation (orchestration) ---------------------------------------


def _factor_rows() -> list[dict]:
    return [
        {
            "factor_type": "egrid",
            "region_code": "TESTSUB",
            "vintage_year": 2022,
            "kg_co2e_per_mwh": 400.0,
            "source_citation": "TEST FIXTURE",
        },
        {
            "factor_type": "greene_residual",
            "region_code": "US",
            "vintage_year": 2022,
            "kg_co2e_per_mwh": 300.0,
            "source_citation": "TEST FIXTURE",
        },
    ]


def _bill_rows() -> list[dict]:
    return [
        {
            "bill_id": 1,
            "canonical_mwh": 100.0,
            "period_start": "2022-01-01",
            "period_end": "2022-12-31",
            "is_estimated_read": False,
            "is_cost_only": False,
            "site_id": 1,
            "energy_carrier": "electricity",
        }
    ]


def test_run_calculation_orchestrates_engine_and_persists(monkeypatch) -> None:
    captured: dict = {}

    monkeypatch.setattr("api.routes.scope2_calc.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr("db.s2_site_store.list_sites", lambda token: [_site_row()])
    monkeypatch.setattr("db.s2_bill_store.list_active_bills", lambda token: _bill_rows())
    monkeypatch.setattr("db.s2_factor_store.load_factors", lambda token: _factor_rows())

    def _save(row, *, org_id, user_id, access_token):
        captured["row"] = row
        return 42

    monkeypatch.setattr("db.s2_calc_store.save_calculation", _save)
    monkeypatch.setattr(
        "db.s2_audit_store.insert_calc_audit_entries",
        lambda entries, *, calc_id, org_id, user_id, access_token: captured.setdefault(
            "audit_calc_id", calc_id
        ),
    )

    resp = client.post(
        "/api/scope2/calculations",
        headers=AUTH_HEADERS,
        json={"reporting_year": 2022},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["calc_id"] == 42
    # 100 MWh x 400 grid = 40,000 location-based
    assert data["location_based_kg_co2e"] == pytest.approx(40_000.0)
    # No instruments -> 100 MWh x 300 residual = 30,000 market-based
    assert data["market_based_kg_co2e"] == pytest.approx(30_000.0)
    assert data["site_count"] == 1
    # Persisted row carries both distinct totals + audit was written for calc 42.
    assert captured["row"]["location_based_kg_co2e"] == pytest.approx(40_000.0)
    assert captured["row"]["market_based_kg_co2e"] == pytest.approx(30_000.0)
    assert captured["audit_calc_id"] == 42


def test_run_calculation_excludes_franchise_sites(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_calc.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr(
        "db.s2_site_store.list_sites",
        lambda token: [_site_row(franchise_flag=True)],
    )
    resp = client.post(
        "/api/scope2/calculations",
        headers=AUTH_HEADERS,
        json={"reporting_year": 2022},
    )
    # Only site is a franchise -> excluded -> nothing to calculate.
    assert resp.status_code == 400


CSV_BODY = {
    "csv_text": "Store,From,To,Usage,Unit\nStore 1,2024-01-01,2024-01-31,1500,kWh\n",
    "mapping": {
        "site_ref": "Store",
        "period_start": "From",
        "period_end": "To",
        "quantity": "Usage",
        "unit": "Unit",
    },
}


def test_commit_csv_persists_bills(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("api.routes.scope2_ingestion.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr(
        "db.s2_site_store.list_sites", lambda token: [_site_row(name="Store 1")]
    )
    monkeypatch.setattr(
        "db.s2_bill_store.get_or_create_account",
        lambda site_id, carrier, *, org_id, user_id, access_token: 5,
    )

    def _insert(rows, *, org_id, user_id, access_token):
        captured["rows"] = rows
        return len(rows)

    monkeypatch.setattr("db.s2_bill_store.insert_bills", _insert)

    resp = client.post("/api/scope2/bills/import-csv", headers=AUTH_HEADERS, json=CSV_BODY)
    assert resp.status_code == 200
    assert resp.json()["committed_count"] == 1
    assert captured["rows"][0]["account_id"] == 5
    assert captured["rows"][0]["canonical_mwh"] == pytest.approx(1.5)


def test_commit_csv_reports_unresolved_site(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_ingestion.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr("db.s2_site_store.list_sites", lambda token: [])  # no matching site
    monkeypatch.setattr(
        "db.s2_bill_store.insert_bills",
        lambda rows, *, org_id, user_id, access_token: 0,
    )
    resp = client.post("/api/scope2/bills/import-csv", headers=AUTH_HEADERS, json=CSV_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert data["committed_count"] == 0
    assert "Store 1" in data["unresolved_site_refs"]


def test_run_calculation_missing_factor_is_422(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_calc.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr("db.s2_site_store.list_sites", lambda token: [_site_row()])
    monkeypatch.setattr("db.s2_bill_store.list_active_bills", lambda token: _bill_rows())
    monkeypatch.setattr("db.s2_factor_store.load_factors", lambda token: [])  # no factors
    resp = client.post(
        "/api/scope2/calculations",
        headers=AUTH_HEADERS,
        json={"reporting_year": 2022},
    )
    assert resp.status_code == 422
