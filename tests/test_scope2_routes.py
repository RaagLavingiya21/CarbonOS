"""Scope 2 API route tests (stores mocked; auth bypassed via conftest).

Exercises site CRUD, CSV preview, and the full run-calculation orchestration
(stores -> engine -> persisted result) without a live database.
"""

from __future__ import annotations

import base64

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
    captured: dict = {}
    monkeypatch.setattr("api.routes.scope2_sites.resolve_org_id", lambda cu: "org-1")

    def _create(payload, *, org_id, user_id, access_token):
        captured["payload"] = payload
        return 1

    monkeypatch.setattr("db.s2_site_store.create_site", _create)
    monkeypatch.setattr("db.s2_site_store.get_site", lambda sid, token: _site_row())

    resp = client.post(
        "/api/scope2/sites",
        headers=AUTH_HEADERS,
        json={"name": "Store 1", "site_type": "retail"},
    )
    assert resp.status_code == 201
    assert resp.json()["site_id"] == 1
    # No None values reach the DB (would violate NOT NULL columns), and boundary
    # fields are filled from the sector template.
    assert None not in captured["payload"].values()
    assert captured["payload"]["ownership"]  # from retail template
    assert captured["payload"]["lease_type"]


def test_egrid_subregions_endpoint() -> None:
    resp = client.get("/api/scope2/egrid-subregions", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    codes = {s["code"] for s in resp.json()}
    assert {"RFCE", "CAMX"} <= codes


def test_create_site_rejects_invalid_subregion() -> None:
    # field_validator fails at request parse -> 422 before the route body runs.
    resp = client.post(
        "/api/scope2/sites",
        headers=AUTH_HEADERS,
        json={"name": "X", "site_type": "retail", "egrid_subregion": "ZZZZ"},
    )
    assert resp.status_code == 422


def test_create_site_accepts_and_normalizes_subregion(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("api.routes.scope2_sites.resolve_org_id", lambda cu: "org-1")

    def _create(payload, *, org_id, user_id, access_token):
        captured["payload"] = payload
        return 1

    monkeypatch.setattr("db.s2_site_store.create_site", _create)
    monkeypatch.setattr(
        "db.s2_site_store.get_site",
        lambda sid, token: _site_row(egrid_subregion="RFCE"),
    )
    resp = client.post(
        "/api/scope2/sites",
        headers=AUTH_HEADERS,
        json={"name": "Store", "site_type": "retail", "egrid_subregion": "rfce"},
    )
    assert resp.status_code == 201
    assert captured["payload"]["egrid_subregion"] == "RFCE"  # normalized to upper


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
        return [{**row, "bill_id": i} for i, row in enumerate(rows, start=1)]

    monkeypatch.setattr("db.s2_bill_store.insert_bills", _insert)
    monkeypatch.setattr("db.s2_bill_store.list_active_bill_keys", lambda ids, token: [])
    monkeypatch.setattr(
        "db.s2_bill_store.supersede_bills", lambda pairs, *, access_token: 0
    )

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
        lambda rows, *, org_id, user_id, access_token: [],
    )
    resp = client.post("/api/scope2/bills/import-csv", headers=AUTH_HEADERS, json=CSV_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert data["committed_count"] == 0
    assert "Store 1" in data["unresolved_site_refs"]


def test_commit_csv_supersedes_prior_estimate(monkeypatch) -> None:
    """A same-period actual read trues up a prior estimate; superseded_count reflects it."""
    captured: dict = {}
    monkeypatch.setattr("api.routes.scope2_ingestion.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr(
        "db.s2_site_store.list_sites", lambda token: [_site_row(name="Store 1")]
    )
    monkeypatch.setattr(
        "db.s2_bill_store.get_or_create_account",
        lambda site_id, carrier, *, org_id, user_id, access_token: 5,
    )
    # The CSV row (from CSV_BODY) is an actual read -> bill_id 20; a prior estimate for
    # the same account+period is already active as bill_id 10.
    monkeypatch.setattr(
        "db.s2_bill_store.insert_bills",
        lambda rows, *, org_id, user_id, access_token: [
            {**row, "bill_id": 20} for row in rows
        ],
    )
    active = [
        {
            "bill_id": 10,
            "account_id": 5,
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "is_estimated_read": True,
            "is_cost_only": False,
        },
        {
            "bill_id": 20,
            "account_id": 5,
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "is_estimated_read": False,
            "is_cost_only": False,
        },
    ]
    monkeypatch.setattr("db.s2_bill_store.list_active_bill_keys", lambda ids, token: active)

    def _supersede(pairs, *, access_token):
        captured["pairs"] = pairs
        return len(pairs)

    monkeypatch.setattr("db.s2_bill_store.supersede_bills", _supersede)

    resp = client.post("/api/scope2/bills/import-csv", headers=AUTH_HEADERS, json=CSV_BODY)
    assert resp.status_code == 200
    assert resp.json()["superseded_count"] == 1
    assert captured["pairs"] == [(10, 20)]  # estimate superseded by the actual


# --- reporting -------------------------------------------------------------


def _calc_row(**kw) -> dict:
    r = {
        "calc_id": 42,
        "org_id": "org-1",
        "reporting_year": 2024,
        "scope": "entity",
        "site_id": None,
        "location_based_kg_co2e": 4625.0,
        "market_based_kg_co2e": 7000.0,
        "consumption_mwh": 12.5,
        "market_tier": None,
        "market_fallback_flagged": False,
        "factor_versions": {},
        "methodology_notes": "GHG Protocol Scope 2 dual-method.",
        "created_at": "2026-01-01T00:00:00Z",
    }
    r.update(kw)
    return r


class _FakeOrg:
    id = "org-1"
    name = "Acme Inc"


def test_report_destinations_endpoint() -> None:
    resp = client.get("/api/scope2/report-destinations", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    keys = {d["key"] for d in resp.json()}
    assert {"standard", "cdp", "amazon"} <= keys


def test_get_report_cdp(monkeypatch) -> None:
    monkeypatch.setattr("db.s2_calc_store.get_calculation", lambda cid, token: _calc_row())
    monkeypatch.setattr("db.s2_site_store.list_sites", lambda token: [])
    monkeypatch.setattr("db.s2_bill_store.list_active_bills", lambda token: [])
    monkeypatch.setattr(
        "db.org_store.get_active_org", lambda token, *, user_id=None: _FakeOrg()
    )
    resp = client.get(
        "/api/scope2/calculations/42/report?destination=cdp", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity"] == "Acme Inc"
    assert data["destination"] == "cdp"
    assert data["csv"]
    joined = " ".join(f"{r['field']}={r['value']}" for r in data["rows"])
    assert "4.625" in joined  # location-based kg -> tCO2e


def test_get_report_missing_calc_404(monkeypatch) -> None:
    monkeypatch.setattr("db.s2_calc_store.get_calculation", lambda cid, token: None)
    resp = client.get("/api/scope2/calculations/999/report", headers=AUTH_HEADERS)
    assert resp.status_code == 404


# --- regulatory disclosures ------------------------------------------------


def _mock_disclosure_deps(monkeypatch, calc=None) -> None:
    monkeypatch.setattr(
        "db.s2_calc_store.get_calculation", lambda cid, token: calc if calc is not None else _calc_row()
    )
    monkeypatch.setattr("db.s2_site_store.list_sites", lambda token: [_site_row()])
    monkeypatch.setattr("db.s2_bill_store.list_active_bills", lambda token: [])
    monkeypatch.setattr("db.org_store.get_active_org", lambda token, *, user_id=None: _FakeOrg())


def test_disclosure_standards_endpoint() -> None:
    resp = client.get("/api/scope2/disclosure-standards", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    keys = {d["key"] for d in resp.json()}
    assert {"sb253", "csrd_e1"} <= keys


def test_get_sb253_disclosure(monkeypatch) -> None:
    _mock_disclosure_deps(monkeypatch)
    resp = client.get(
        "/api/scope2/calculations/42/disclosure?standard=sb253", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["standard"] == "sb253"
    assert data["entity"] == "Acme Inc"
    titles = [s["title"] for s in data["sections"]]
    assert any("Scope 2 emissions" in t for t in titles)
    assert "ready" in data["readiness"]
    assert data["csv"]


def test_get_csrd_disclosure_has_e1_sections(monkeypatch) -> None:
    _mock_disclosure_deps(monkeypatch)
    resp = client.get(
        "/api/scope2/calculations/42/disclosure?standard=csrd_e1", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    titles = [s["title"] for s in resp.json()["sections"]]
    assert any("E1-6" in t for t in titles)
    assert any("E1-5" in t for t in titles)


def test_disclosure_unknown_standard_422(monkeypatch) -> None:
    _mock_disclosure_deps(monkeypatch)
    resp = client.get(
        "/api/scope2/calculations/42/disclosure?standard=tcfd", headers=AUTH_HEADERS
    )
    assert resp.status_code == 422


def test_disclosure_missing_calc_404(monkeypatch) -> None:
    monkeypatch.setattr("db.s2_calc_store.get_calculation", lambda cid, token: None)
    resp = client.get("/api/scope2/calculations/999/disclosure", headers=AUTH_HEADERS)
    assert resp.status_code == 404


def test_disclosure_readiness_flags_fallback(monkeypatch) -> None:
    _mock_disclosure_deps(monkeypatch, calc=_calc_row(market_fallback_flagged=True))
    resp = client.get("/api/scope2/calculations/42/disclosure?standard=sb253", headers=AUTH_HEADERS)
    warnings = " ".join(resp.json()["readiness"]["warnings"])
    assert "EAC" in warnings


def test_get_report_bad_destination_422(monkeypatch) -> None:
    monkeypatch.setattr("db.s2_calc_store.get_calculation", lambda cid, token: _calc_row())
    monkeypatch.setattr("db.s2_site_store.list_sites", lambda token: [])
    monkeypatch.setattr("db.s2_bill_store.list_active_bills", lambda token: [])
    monkeypatch.setattr(
        "db.org_store.get_active_org", lambda token, *, user_id=None: _FakeOrg()
    )
    resp = client.get(
        "/api/scope2/calculations/42/report?destination=bogus", headers=AUTH_HEADERS
    )
    assert resp.status_code == 422


# --- inbound buyer request queue -------------------------------------------


def _buyer_row(**kw) -> dict:
    r = {
        "request_id": 5,
        "org_id": "org-1",
        "buyer_name": "Walmart",
        "destination": "cdp",
        "reporting_year": 2024,
        "due_date": None,
        "status": "open",
        "calc_id": None,
        "answered_at": None,
        "notes": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    r.update(kw)
    return r


def test_create_buyer_request(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_reports.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr(
        "db.s2_buyer_request_store.create_request",
        lambda payload, *, org_id, user_id, access_token: 5,
    )
    monkeypatch.setattr(
        "db.s2_buyer_request_store.get_request", lambda rid, token: _buyer_row()
    )
    resp = client.post(
        "/api/scope2/buyer-requests",
        headers=AUTH_HEADERS,
        json={"buyer_name": "Walmart", "destination": "cdp"},
    )
    assert resp.status_code == 201
    assert resp.json()["buyer_name"] == "Walmart"


def test_list_buyer_requests_flags_overdue(monkeypatch) -> None:
    monkeypatch.setattr(
        "db.s2_buyer_request_store.list_requests",
        lambda token: [_buyer_row(due_date="2000-01-01", status="open")],
    )
    resp = client.get("/api/scope2/buyer-requests", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()[0]["is_overdue"] is True


def test_answer_buyer_request_stamps_time(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(
        "db.s2_buyer_request_store.get_request",
        lambda rid, token: _buyer_row(status="open", answered_at=None),
    )

    def _update(rid, updates, *, access_token):
        captured["updates"] = updates
        return _buyer_row(status="answered")

    monkeypatch.setattr("db.s2_buyer_request_store.update_request", _update)
    resp = client.patch(
        "/api/scope2/buyer-requests/5",
        headers=AUTH_HEADERS,
        json={"status": "answered"},
    )
    assert resp.status_code == 200
    assert "answered_at" in captured["updates"]


def test_delete_buyer_request_404(monkeypatch) -> None:
    def _raise(rid, *, access_token):
        raise ValueError("nope")

    monkeypatch.setattr("db.s2_buyer_request_store.delete_request", _raise)
    resp = client.delete("/api/scope2/buyer-requests/999", headers=AUTH_HEADERS)
    assert resp.status_code == 404


# --- coverage scoring ------------------------------------------------------


def test_coverage_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "db.s2_site_store.list_sites",
        lambda token: [_site_row(site_id=1), _site_row(site_id=2)],
    )
    monkeypatch.setattr(
        "db.s2_bill_store.list_active_bills",
        lambda token: [
            {
                "site_id": 1,
                "canonical_mwh": 90.0,
                "is_estimated_read": False,
                "ingestion_method": "csv",
            },
            {
                "site_id": 1,
                "canonical_mwh": 10.0,
                "is_estimated_read": True,
                "ingestion_method": "estimate",
            },
        ],
    )
    resp = client.get("/api/scope2/coverage", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["coverage_fraction"] == pytest.approx(0.9)
    assert data["sites_missing_data"] == 1  # site 2 has no data


# --- documented estimation fallback ----------------------------------------


def test_estimate_site_persists_labeled_estimate(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("api.routes.scope2_ingestion.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr(
        "db.s2_site_store.get_site", lambda sid, token: _site_row(site_type="retail")
    )
    monkeypatch.setattr(
        "db.s2_bill_store.get_or_create_account",
        lambda site_id, carrier, *, org_id, user_id, access_token: 9,
    )

    def _insert(rows, *, org_id, user_id, access_token):
        captured["rows"] = rows
        return [{**row, "bill_id": i} for i, row in enumerate(rows, start=1)]

    monkeypatch.setattr("db.s2_bill_store.insert_bills", _insert)
    monkeypatch.setattr("db.s2_bill_store.list_active_bill_keys", lambda ids, token: [])
    monkeypatch.setattr(
        "db.s2_bill_store.supersede_bills", lambda pairs, *, access_token: 0
    )

    resp = client.post(
        "/api/scope2/sites/1/estimate",
        headers=AUTH_HEADERS,
        json={"floor_area_sqft": 20000, "reporting_year": 2024},
    )
    assert resp.status_code == 200
    assert resp.json()["annual_mwh"] == pytest.approx(280.0)
    bill = captured["rows"][0]
    assert bill["is_estimated_read"] is True
    assert bill["ingestion_method"] == "estimate"
    assert bill["canonical_mwh"] == pytest.approx(280.0)
    assert "ESTIMATE" in bill["conversion_note"]


def test_estimate_site_404_for_missing_site(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_ingestion.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr("db.s2_site_store.get_site", lambda sid, token: None)
    resp = client.post(
        "/api/scope2/sites/999/estimate",
        headers=AUTH_HEADERS,
        json={"floor_area_sqft": 1000, "reporting_year": 2024},
    )
    assert resp.status_code == 404


# --- PDF/OCR document ingestion --------------------------------------------

_DOC_BODY = {"file_base64": base64.b64encode(b"%PDF-fake").decode(), "content_type": "application/pdf"}


def _fake_extraction(meters, header=None):
    from s2_ingestion.ocr import BillExtraction, ExtractedField, MeterExtraction

    def _f(v, c=0.98):
        return ExtractedField(v, c)

    hdr = {k: _f(v) for k, v in (header or {"utility_name": "PG&E"}).items()}
    return BillExtraction(
        header=hdr,
        meters=[MeterExtraction(fields={k: _f(*(m[k] if isinstance(m[k], tuple) else (m[k],))) for k in m}) for m in meters],
        model="test-model",
    )


def test_extract_doc_returns_meters_and_review_flag(monkeypatch) -> None:
    meter = {
        "meter_number": "M1",
        "energy_carrier": "Electricity",
        "service_period_start": "2025-01-01",
        "service_period_end": "2025-01-31",
        "consumption_quantity": "1500",
        "consumption_unit": "kWh",
        "total_cost_usd": "$210",
        "is_estimated_read": "false",
    }
    monkeypatch.setattr(
        "api.routes.scope2_ingestion.extract_bill_document",
        lambda data, ct, **kw: _fake_extraction([meter]),
    )
    resp = client.post("/api/scope2/bills/extract-doc", headers=AUTH_HEADERS, json=_DOC_BODY)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["meters"]) == 1
    assert data["meters"][0]["canonical_mwh"] == 1.5
    assert data["meters"][0]["energy_carrier"] == "electricity"
    assert data["needs_review"] is False


def test_extract_doc_flags_low_confidence_for_review(monkeypatch) -> None:
    meter = {
        "energy_carrier": "Electricity",
        "service_period_start": "2025-01-01",
        "service_period_end": "2025-01-31",
        "consumption_quantity": ("1500", 0.4),  # below REVIEW_THRESHOLD
        "consumption_unit": "kWh",
    }
    monkeypatch.setattr(
        "api.routes.scope2_ingestion.extract_bill_document",
        lambda data, ct, **kw: _fake_extraction([meter]),
    )
    resp = client.post("/api/scope2/bills/extract-doc", headers=AUTH_HEADERS, json=_DOC_BODY)
    assert resp.json()["needs_review"] is True


def test_extract_doc_rejects_bad_base64() -> None:
    resp = client.post(
        "/api/scope2/bills/extract-doc",
        headers=AUTH_HEADERS,
        json={"file_base64": "!!!not-base64!!!", "content_type": "application/pdf"},
    )
    assert resp.status_code == 422


def test_import_doc_persists_and_dedups(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr("api.routes.scope2_ingestion.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr("db.s2_site_store.get_site", lambda sid, token: _site_row())
    monkeypatch.setattr(
        "db.s2_bill_store.get_or_create_account",
        lambda site_id, carrier, *, org_id, user_id, access_token, source_type: {"electricity": 5, "natural_gas": 6}[carrier],
    )

    def _insert(rows, *, org_id, user_id, access_token):
        captured["rows"] = rows
        return [{**r, "bill_id": i} for i, r in enumerate(rows, start=1)]

    monkeypatch.setattr("db.s2_bill_store.insert_bills", _insert)
    monkeypatch.setattr("db.s2_bill_store.list_active_bill_keys", lambda ids, token: [])
    monkeypatch.setattr("db.s2_bill_store.supersede_bills", lambda pairs, *, access_token: 0)

    body = {
        "site_id": 1,
        "meters": [
            {"energy_carrier": "electricity", "period_start": "2025-01-01", "period_end": "2025-01-31", "canonical_mwh": 1.5},
            {"energy_carrier": "natural_gas", "period_start": "2025-01-01", "period_end": "2025-01-31", "canonical_mwh": 29.3},
            {"energy_carrier": "plutonium", "period_start": "2025-01-01", "period_end": "2025-01-31"},  # skipped
        ],
    }
    resp = client.post("/api/scope2/bills/import-doc", headers=AUTH_HEADERS, json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["committed_count"] == 2
    assert data["skipped_count"] == 1
    assert captured["rows"][0]["ingestion_method"] == "pdf_ocr"


def test_import_doc_404_for_missing_site(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_ingestion.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr("db.s2_site_store.get_site", lambda sid, token: None)
    resp = client.post(
        "/api/scope2/bills/import-doc",
        headers=AUTH_HEADERS,
        json={"site_id": 999, "meters": []},
    )
    assert resp.status_code == 404


# --- leased-site landlord workflow -----------------------------------------


def _landlord_row(**kw) -> dict:
    row = {
        "request_id": 7,
        "site_id": 1,
        "site_name": "Store 1",
        "landlord_contact": "mgr@example.com",
        "method": "email",
        "status": "draft",
        "sent_at": None,
        "responded_at": None,
        "reminder_cadence_days": 14,
        "returned_data_ref": None,
        "notes": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    row.update(kw)
    return row


def test_create_landlord_request(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.scope2_landlord.resolve_org_id", lambda cu: "org-1")
    monkeypatch.setattr(
        "db.s2_landlord_store.create_request",
        lambda payload, *, org_id, user_id, access_token: 7,
    )
    monkeypatch.setattr(
        "db.s2_landlord_store.get_request", lambda rid, token: _landlord_row()
    )
    resp = client.post(
        "/api/scope2/landlord-requests",
        headers=AUTH_HEADERS,
        json={"site_id": 1, "landlord_contact": "mgr@example.com"},
    )
    assert resp.status_code == 201
    assert resp.json()["request_id"] == 7
    assert resp.json()["status"] == "draft"


def test_update_landlord_status_sent_stamps_time(monkeypatch) -> None:
    captured: dict = {}
    monkeypatch.setattr(
        "db.s2_landlord_store.get_request",
        lambda rid, token: _landlord_row(status="draft", sent_at=None),
    )

    def _update(rid, updates, *, access_token):
        captured["updates"] = updates
        return _landlord_row(status="sent", sent_at=updates.get("sent_at"))

    monkeypatch.setattr("db.s2_landlord_store.update_request", _update)
    resp = client.patch(
        "/api/scope2/landlord-requests/7",
        headers=AUTH_HEADERS,
        json={"status": "sent"},
    )
    assert resp.status_code == 200
    # Transition to 'sent' auto-stamps sent_at.
    assert "sent_at" in captured["updates"]
    assert resp.json()["status"] == "sent"


def test_delete_landlord_request_404(monkeypatch) -> None:
    def _raise(rid, *, access_token):
        raise ValueError("not found")

    monkeypatch.setattr("db.s2_landlord_store.delete_request", _raise)
    resp = client.delete("/api/scope2/landlord-requests/999", headers=AUTH_HEADERS)
    assert resp.status_code == 404


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
