"""API tests for the Scope 1 routes.

Auth is bypassed by the autouse conftest fixture; store calls are monkeypatched
so no live Supabase is needed (same pattern as tests/test_api.py).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


def test_consolidation_preview_is_pure() -> None:
    resp = client.post(
        "/api/scope1/consolidation/preview",
        json={"approach": "equity_share", "economic_interest_pct": 40.0},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["multiplier"] == 0.40


def test_create_entity_delegates_to_store(monkeypatch) -> None:
    def fake_create_entity(data, *, access_token, user_id):
        return {"id": "e1", **data}

    monkeypatch.setattr("db.scope1_store.create_entity", fake_create_entity)
    resp = client.post(
        "/api/scope1/entities",
        json={"name": "Acme Mfg", "jurisdiction": "US", "entity_type": "parent",
              "effective_from": "2025-01-01"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "e1"
    assert resp.json()["name"] == "Acme Mfg"


def test_stationary_record_computes_gas_masses(monkeypatch) -> None:
    """The route runs the calc engine and persists gas masses (never CO2e)."""
    captured: dict = {}

    def fake_create_record(row, *, access_token, user_id):
        captured.update(row)
        return {"id": "rec1", **row}

    monkeypatch.setattr("db.scope1_store.create_record", fake_create_record)
    monkeypatch.setattr("db.scope1_store.upsert_collection_status", lambda row, **k: row)
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    resp = client.post(
        "/api/scope1/records/stationary",
        json={
            "inventory_id": "inv1", "emission_source_id": "src1",
            "period_start": "2025-01-01", "period_end": "2025-01-31",
            "fuel_or_activity": "natural_gas", "activity_value": 1000,
            "activity_unit": "therms", "data_quality_tier": 2,
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert captured["kg_co2_fossil"] == 5306.0
    assert captured["kg_ch4"] == 0.100
    assert captured["kg_n2o"] == 0.010
    assert captured["biogenic_fossil_tag"] == "fossil"
    assert captured["ef_tier"] == "T1"
    assert "CFR" in captured["ef_source"]
    assert "kg_co2e" not in captured and "co2e" not in captured  # no CO2e stored


def test_stationary_record_unknown_fuel_returns_422(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.create_record", lambda row, **k: row)
    resp = client.post(
        "/api/scope1/records/stationary",
        json={"inventory_id": "inv1", "emission_source_id": "src1",
              "period_start": "2025-01-01", "period_end": "2025-01-31",
              "fuel_or_activity": "unobtanium", "activity_value": 10,
              "activity_unit": "mmBtu"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 422


def test_inventory_report_rollup(monkeypatch) -> None:
    record = {
        "id": "rec1", "inventory_id": "inv1", "emission_source_id": "src1",
        "kg_co2_fossil": 5306.0, "kg_ch4": 0.100, "kg_n2o": 0.010,
        "kg_co2_biogenic": 0.0,
    }
    monkeypatch.setattr("db.scope1_store.list_records_for_inventory",
                        lambda inv, **k: [record])
    monkeypatch.setattr("db.scope1_store.list_sources",
                        lambda **k: [{"id": "src1", "entity_id": "e1",
                                      "facility_id": "f1", "source_name": "Boiler 1"}])
    monkeypatch.setattr("db.scope1_store.list_facilities",
                        lambda **k: [{"id": "f1", "name": "Plant A"}])
    monkeypatch.setattr("db.scope1_store.list_boundaries",
                        lambda inv, **k: [{"entity_id": "e1", "consolidation_multiplier": 1.0}])

    resp = client.get("/api/scope1/inventories/inv1/report?ar_version=AR5", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_scope1_tco2e"] == round((5306.0 + 0.1 * 28 + 0.01 * 265) / 1000.0, 10)
    assert body["by_facility"][0]["facility_name"] == "Plant A"
    assert body["record_count"] == 1


def test_report_applies_consolidation_multiplier(monkeypatch) -> None:
    record = {"id": "rec1", "inventory_id": "inv1", "emission_source_id": "src1",
              "kg_co2_fossil": 1000.0, "kg_ch4": 0.0, "kg_n2o": 0.0, "kg_co2_biogenic": 0.0}
    monkeypatch.setattr("db.scope1_store.list_records_for_inventory", lambda inv, **k: [record])
    monkeypatch.setattr("db.scope1_store.list_sources",
                        lambda **k: [{"id": "src1", "entity_id": "e1", "facility_id": "f1",
                                      "source_name": "JV boiler"}])
    monkeypatch.setattr("db.scope1_store.list_facilities", lambda **k: [{"id": "f1", "name": "JV"}])
    monkeypatch.setattr("db.scope1_store.list_boundaries",
                        lambda inv, **k: [{"entity_id": "e1", "consolidation_multiplier": 0.40}])

    resp = client.get("/api/scope1/inventories/inv1/report", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    # 1000 kg CO2 x 0.40 = 0.4 tCO2e
    assert resp.json()["total_scope1_tco2e"] == 0.4


# --- Data-collection orchestration ------------------------------------------

def test_assign_owner(monkeypatch) -> None:
    monkeypatch.setattr(
        "db.scope1_store.assign_source_owner",
        lambda source_id, owner_id, **k: {"emission_source_id": source_id, "data_owner_id": owner_id},
    )
    resp = client.post(
        "/api/scope1/sources/src1/assign-owner",
        json={"data_owner_id": "owner1"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["data_owner_id"] == "owner1"


def test_collection_init_only_covers_in_scope_untracked_sources(monkeypatch) -> None:
    captured: list[dict] = []
    monkeypatch.setattr(
        "db.scope1_store.get_inventory",
        lambda inv, **k: {"id": inv, "period_start": "2025-01-01", "period_end": "2025-12-31"},
    )
    monkeypatch.setattr(
        "db.scope1_store.list_sources",
        lambda **k: [
            {"id": "src1", "is_excluded": False},
            {"id": "src2", "is_excluded": True},          # excluded -> skipped
            {"id": "src3", "is_excluded": False},          # already tracked -> skipped
        ],
    )
    monkeypatch.setattr(
        "db.scope1_store.list_collection_status",
        lambda inv, **k: [{"emission_source_id": "src3", "status": "missing"}],
    )

    def fake_upsert(row, **k):
        captured.append(row)
        return row

    monkeypatch.setattr("db.scope1_store.upsert_collection_status", fake_upsert)

    resp = client.post("/api/scope1/inventories/inv1/collection/init", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert [r["emission_source_id"] for r in captured] == ["src1"]
    assert captured[0]["status"] == "missing"


def test_set_collection_status(monkeypatch) -> None:
    monkeypatch.setattr("db.scope1_store.upsert_collection_status", lambda row, **k: row)
    resp = client.post(
        "/api/scope1/collection/status",
        json={
            "inventory_id": "inv1", "emission_source_id": "src1",
            "period_start": "2025-01-01", "period_end": "2025-12-31",
            "status": "received", "data_owner_id": "owner1",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "received"


def test_record_creation_auto_advances_collection(monkeypatch) -> None:
    advanced: dict = {}
    monkeypatch.setattr("db.scope1_store.create_record", lambda row, **k: {"id": "rec1", **row})
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})

    def fake_upsert(row, **k):
        advanced.update(row)
        return row

    monkeypatch.setattr("db.scope1_store.upsert_collection_status", fake_upsert)
    resp = client.post(
        "/api/scope1/records/stationary",
        json={
            "inventory_id": "inv1", "emission_source_id": "src1",
            "period_start": "2025-01-01", "period_end": "2025-12-31",
            "fuel_or_activity": "natural_gas", "activity_value": 1000, "activity_unit": "therms",
        },
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert advanced["status"] == "entered"
    assert advanced["emission_source_id"] == "src1"


def test_readiness_counts_completeness(monkeypatch) -> None:
    monkeypatch.setattr(
        "db.scope1_store.list_collection_status",
        lambda inv, **k: [
            {"emission_source_id": "s1", "status": "entered"},
            {"emission_source_id": "s2", "status": "verified"},
            {"emission_source_id": "s3", "status": "missing"},
            {"emission_source_id": "s4", "status": "requested"},
        ],
    )
    resp = client.get("/api/scope1/inventories/inv1/readiness", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 4
    assert body["complete"] == 2          # entered + verified
    assert body["completeness_pct"] == 50.0
    assert body["by_status"]["missing"] == 1


# --- Evidence + audit trail -------------------------------------------------

def test_evidence_row_computes_sha256() -> None:
    """Pure hashing/pathing — the tamper-evidence backbone."""
    import hashlib

    from db.scope1_store import evidence_row

    data = b"utility invoice bytes"
    row = evidence_row(
        data, file_name="bill.pdf", content_type="application/pdf",
        document_type="utility_invoice", org_id="org1", inventory_id="inv1", user_id="u1",
    )
    assert row["hash_sha256"] == hashlib.sha256(data).hexdigest()
    assert row["byte_size"] == len(data)
    assert row["storage_uri"].startswith("org1/inv1/")
    assert row["storage_uri"].endswith("-bill.pdf")
    assert row["document_type"] == "utility_invoice"


def test_upload_evidence_route(monkeypatch) -> None:
    captured: dict = {}

    def fake_upload(data, *, file_name, content_type, document_type, inventory_id, **k):
        captured.update(data=data, file_name=file_name, document_type=document_type)
        return {"id": "ev1", "file_name": file_name, "hash_sha256": "deadbeef"}

    monkeypatch.setattr("db.scope1_store.upload_evidence", fake_upload)
    resp = client.post(
        "/api/scope1/evidence",
        files={"file": ("bill.pdf", b"PDFBYTES", "application/pdf")},
        data={"inventory_id": "inv1", "document_type": "utility_invoice"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "ev1"
    assert captured["data"] == b"PDFBYTES"
    assert captured["document_type"] == "utility_invoice"


def test_record_create_writes_audit(monkeypatch) -> None:
    logged: dict = {}
    monkeypatch.setattr("db.scope1_store.create_record", lambda row, **k: {"id": "rec9", **row})
    monkeypatch.setattr("db.scope1_store.upsert_collection_status", lambda row, **k: row)

    def fake_log(entity_table, entity_id, action, **k):
        logged.update(table=entity_table, id=entity_id, action=action)
        return {}

    monkeypatch.setattr("db.scope1_store.log_change", fake_log)
    resp = client.post(
        "/api/scope1/records/stationary",
        json={"inventory_id": "inv1", "emission_source_id": "src1",
              "period_start": "2025-01-01", "period_end": "2025-12-31",
              "fuel_or_activity": "natural_gas", "activity_value": 1000, "activity_unit": "therms"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert logged == {"table": "s1_emission_record", "id": "rec9", "action": "create"}


def test_lock_writes_audit(monkeypatch) -> None:
    logged: dict = {}
    monkeypatch.setattr("db.scope1_store.lock_inventory", lambda inv, **k: {"id": inv, "locked": True})
    monkeypatch.setattr(
        "db.scope1_store.log_change",
        lambda table, entity_id, action, **k: logged.update(table=table, action=action) or {},
    )
    resp = client.post("/api/scope1/inventories/inv1/lock", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert logged["table"] == "s1_inventory"
    assert logged["action"] == "lock"


def test_record_audit_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        "db.scope1_store.list_change_log",
        lambda table, entity_id, **k: [{"action": "create", "entity_id": entity_id}],
    )
    resp = client.get("/api/scope1/records/rec1/audit", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()[0]["action"] == "create"


# --- CSV bulk intake --------------------------------------------------------

def test_csv_bulk_intake(monkeypatch) -> None:
    created: list[dict] = []
    monkeypatch.setattr(
        "db.scope1_store.get_inventory",
        lambda inv, **k: {"id": inv, "period_start": "2025-01-01", "period_end": "2025-12-31"},
    )
    monkeypatch.setattr(
        "db.scope1_store.list_sources",
        lambda **k: [
            {"id": "srcA", "source_name": "Boiler 1"},
            {"id": "srcB", "source_name": "Van"},
        ],
    )

    def fake_create(row, **k):
        created.append(row)
        return {"id": f"rec{len(created)}", **row}

    monkeypatch.setattr("db.scope1_store.create_record", fake_create)
    monkeypatch.setattr("db.scope1_store.upsert_collection_status", lambda row, **k: row)
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})

    csv_text = (
        "source_name,category,fuel,amount,unit\n"
        "Boiler 1,stationary,natural_gas,1000,therms\n"    # ok
        "Van,mobile,motor_gasoline,400,gal\n"              # ok
        "Ghost,stationary,natural_gas,10,therms\n"         # unknown source
        "Boiler 1,stationary,unobtanium,10,mmBtu\n"        # missing EF
    )
    resp = client.post(
        "/api/scope1/records/csv",
        files={"file": ("data.csv", csv_text.encode(), "text/csv")},
        data={"inventory_id": "inv1"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created"] == 2
    assert len(body["row_errors"]) == 2                    # unknown source + missing EF
    assert created[0]["kg_co2_fossil"] == 5306.0           # NG computed through the shared path
    assert created[0]["activity_data_source"] == "csv"


# --- OCR review queue -------------------------------------------------------

def test_ocr_extract_route(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.scope1.start_ocr",
        lambda sid, dk, b64, ct: {
            "extraction": {"consumption_quantity": {"value": "1000", "confidence": 0.6}},
            "needs_review": True, "min_confidence": 0.6},
    )
    monkeypatch.setattr("db.scope1_store.upload_evidence",
                        lambda data, **k: {"id": "ev1", "hash_sha256": "abc"})
    captured: dict = {}
    monkeypatch.setattr("db.scope1_store.create_ocr_extraction",
                        lambda row, **k: captured.update(row) or {"id": "ocr1", **row})
    resp = client.post(
        "/api/scope1/ocr/extract",
        files={"file": ("bill.pdf", b"PDFBYTES", "application/pdf")},
        data={"doc_kind": "utility_bill", "inventory_id": "inv1"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_review"
    assert resp.json()["needs_review"] is True
    assert captured["evidence_document_id"] == "ev1"
    assert captured["graph_session_id"]


def test_ocr_review_approve_creates_record(monkeypatch) -> None:
    monkeypatch.setattr(
        "db.scope1_store.get_ocr_extraction",
        lambda eid, **k: {"id": eid, "graph_session_id": "s1", "inventory_id": "inv1",
                          "evidence_document_id": "ev1", "status": "pending_review"},
    )
    monkeypatch.setattr("api.routes.scope1.get_ocr_state", lambda sid: None)   # skip graph resume
    created: dict = {}
    monkeypatch.setattr("db.scope1_store.create_record",
                        lambda row, **k: created.update(row) or {"id": "rec1", **row})
    monkeypatch.setattr("db.scope1_store.upsert_collection_status", lambda row, **k: row)
    monkeypatch.setattr("db.scope1_store.log_change", lambda *a, **k: {})
    updated: dict = {}
    monkeypatch.setattr("db.scope1_store.update_ocr_extraction",
                        lambda eid, patch, **k: updated.update(patch) or {"id": eid, **patch})
    resp = client.post(
        "/api/scope1/ocr/ocr1/review",
        json={"action": "approve", "emission_source_id": "src1",
              "fuel_or_activity": "natural_gas", "activity_value": 1000,
              "activity_unit": "therms", "period_start": "2025-01-01",
              "period_end": "2025-12-31"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert created["kg_co2_fossil"] == 5306.0
    assert created["evidence_document_id"] == "ev1"
    assert created["activity_data_source"] == "ocr"
    assert updated["status"] == "applied"
    assert updated["applied_record_id"] == "rec1"


def test_ocr_review_reject(monkeypatch) -> None:
    monkeypatch.setattr(
        "db.scope1_store.get_ocr_extraction",
        lambda eid, **k: {"id": eid, "graph_session_id": "s1", "status": "pending_review"},
    )
    monkeypatch.setattr("api.routes.scope1.get_ocr_state", lambda sid: None)
    monkeypatch.setattr("db.scope1_store.update_ocr_extraction",
                        lambda eid, patch, **k: {"id": eid, **patch})
    resp = client.post("/api/scope1/ocr/ocr1/review", json={"action": "reject"}, headers=AUTH_HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
