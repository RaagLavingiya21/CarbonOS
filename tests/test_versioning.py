from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from calc.footprint import FootprintResult, LineItem
from db import store as store_module
from tests.conftest import AUTH_HEADERS, TEST_ACCESS_TOKEN, TEST_USER_ID

client = TestClient(app)

LINEAGE_A = "11111111-1111-1111-1111-111111111111"
LINEAGE_B = "22222222-2222-2222-2222-222222222222"


def _sample_result() -> FootprintResult:
    line_item = LineItem(
        row_index=0,
        component="body",
        material="cotton",
        quantity=1.0,
        spend_usd=10.0,
        weight_kg=None,
        supplier=None,
        country_of_origin=None,
        sector_name="Cotton farming",
        sector_code="1119A0",
        ef_kg_co2e_per_usd=2.0,
        ef_source="Test",
        ef_confidence=100.0,
        kg_co2e=20.0,
        share_pct=100.0,
        is_matched=True,
        is_low_confidence=False,
        is_no_ef_match=False,
        is_flagged_by_parser=False,
    )
    return FootprintResult(
        product_name="Test Product",
        total_kg_co2e=20.0,
        line_items=[line_item],
        matched_count=1,
        flagged_count=0,
        unmatched_count=0,
        completeness_pct=100.0,
    )


def _mock_supabase_insert(monkeypatch: pytest.MonkeyPatch, captured: dict) -> None:
    def fake_table(name: str) -> MagicMock:
        mock_table = MagicMock()
        if name == "products":
            mock_insert = MagicMock()
            mock_execute = MagicMock()

            def capture_insert(data: dict) -> MagicMock:
                captured["insert"] = data
                mock_execute.data = [{"product_id": captured.get("product_id", 99)}]
                mock_insert.execute = MagicMock(return_value=mock_execute)
                return mock_insert

            mock_table.insert = capture_insert
        else:
            mock_table.insert.return_value.execute.return_value = MagicMock(data=[])
        return mock_table

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)


def test_save_without_recalculate_sets_version_one_and_fresh_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}
    _mock_supabase_insert(monkeypatch, captured)

    product_id = store_module.save_analysis(
        "Fresh Product",
        _sample_result(),
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )

    assert product_id == 99
    assert captured["insert"]["version"] == 1
    assert "product_lineage_id" not in captured["insert"]


def test_save_with_recalculate_reuses_lineage_and_increments_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {"product_id": 100}
    _mock_supabase_insert(monkeypatch, captured)
    monkeypatch.setattr(
        store_module,
        "get_product_by_id",
        lambda product_id, access_token: {
            "product_id": product_id,
            "product_lineage_id": LINEAGE_A,
            "version": 2,
        },
    )

    product_id = store_module.save_analysis(
        "Recalculated Product",
        _sample_result(),
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
        recalculate_of_product_id=5,
    )

    assert product_id == 100
    assert captured["insert"]["product_lineage_id"] == LINEAGE_A
    assert captured["insert"]["version"] == 3


def test_publish_analysis_succeeds_from_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    updates: list[dict] = []
    mock_table = MagicMock()
    mock_update = MagicMock()
    mock_eq = MagicMock()
    mock_eq.execute = MagicMock()
    mock_update.eq.return_value = mock_eq
    mock_table.update = lambda data: (updates.append(data), mock_update)[1]
    mock_client = MagicMock()
    mock_client.table.return_value = mock_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        store_module,
        "get_product_by_id",
        lambda product_id, access_token: {
            "product_id": product_id,
            "product_name": "Approved Product",
            "status": "approved",
        },
    )
    audit_calls: list[dict] = []
    monkeypatch.setattr(
        store_module,
        "append_audit_log",
        lambda **kwargs: audit_calls.append(kwargs),
    )

    store_module.publish_analysis(1, user_id=TEST_USER_ID, access_token=TEST_ACCESS_TOKEN)

    assert updates[0]["status"] == "published"
    assert updates[0]["published_at"]
    assert audit_calls[0]["event"] == "published"
    assert audit_calls[0]["workflow"] == "footprint_lifecycle"


@pytest.mark.parametrize(
    "status",
    ["flagged", "published"],
)
def test_publish_analysis_rejects_non_approved(status: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        store_module,
        "get_product_by_id",
        lambda product_id, access_token: {
            "product_id": product_id,
            "product_name": "Product",
            "status": status,
        },
    )

    with pytest.raises(ValueError, match="Only approved footprints can be published"):
        store_module.publish_analysis(1, user_id=TEST_USER_ID, access_token=TEST_ACCESS_TOKEN)


def test_list_analyses_filters_by_status(monkeypatch: pytest.MonkeyPatch) -> None:
    products = [
        {
            "product_id": 1,
            "product_name": "Published Product",
            "analysis_date": str(date.today()),
            "total_kg_co2e": 10.0,
            "matched_items": 1,
            "flagged_items": 0,
            "status": "published",
            "version": 1,
        }
    ]
    captured: dict = {}

    def fake_get_products(access_token, *, user_id=None, status=None):
        captured["status"] = status
        return products if status == "published" else []

    monkeypatch.setattr("api.routes.analyzer.get_products_for_active_org", fake_get_products)

    response = client.get("/api/analyses?status=published", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert captured["status"] == "published"
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "published"


def test_publish_route_returns_404_for_missing_product(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.routes.analyzer.get_product_by_id",
        lambda product_id, access_token: None,
    )

    response = client.post("/api/analyses/999/publish", headers=AUTH_HEADERS)

    assert response.status_code == 404


def test_publish_route_returns_409_for_non_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_publish(product_id: int, *, user_id: str, access_token: str) -> None:
        raise ValueError("Only approved footprints can be published.")

    monkeypatch.setattr(
        "api.routes.analyzer.get_product_by_id",
        lambda product_id, access_token: {
            "product_id": product_id,
            "status": "flagged",
        },
    )
    monkeypatch.setattr("api.routes.analyzer.publish_analysis", fake_publish)

    response = client.post("/api/analyses/1/publish", headers=AUTH_HEADERS)

    assert response.status_code == 409


def test_portfolio_summary_aggregates_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.routes.analyzer.get_products_for_active_org",
        lambda access_token, user_id=None, status=None: [
            {
                "product_id": 1,
                "total_kg_co2e": 100.0,
                "primary_data_share": 0.2,
                "flagged_items": 2,
                "status": "approved",
            },
            {
                "product_id": 2,
                "total_kg_co2e": 50.0,
                "primary_data_share": 0.4,
                "flagged_items": 0,
                "status": "published",
            },
            {
                "product_id": 3,
                "total_kg_co2e": 25.0,
                "primary_data_share": 0.0,
                "flagged_items": 1,
                "status": "flagged",
            },
        ],
    )

    response = client.get("/api/analyses/summary", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_kg_co2e"] == 175.0
    assert payload["avg_primary_data_share"] == pytest.approx(0.2)
    assert payload["open_flags_count"] == 2
    assert payload["counts_by_status"] == {"approved": 1, "published": 1, "flagged": 1}
    assert payload["product_count"] == 3


def _source_product_with_line_items() -> dict:
    return {
        "product_id": 5,
        "product_name": "Test Product",
        "analysis_date": "2025-06-15",
        "total_kg_co2e": 30.0,
        "matched_items": 2,
        "flagged_items": 0,
        "status": "approved",
        "flagged_comment": None,
        "product_description": "Desc",
        "declared_unit": "piece",
        "unitary_product_amount": 1.0,
        "system_boundary": "cradle-to-gate",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "geography_country": None,
        "primary_data_share": 0.0,
        "spec_version": "3.0.0",
        "product_lineage_id": LINEAGE_A,
        "version": 1,
        "line_items": [
            {
                "item_id": 10,
                "component": "body",
                "material": "cotton",
                "spend_usd": 10.0,
                "matched_sector": "Cotton farming",
                "emission_factor": 2.0,
                "ef_source": "CEDA",
                "kg_co2e": 20.0,
                "share_pct": 66.6667,
                "flag_status": "ok",
                "data_source": "secondary",
            },
            {
                "item_id": 11,
                "component": "trim",
                "material": "polyester",
                "spend_usd": 5.0,
                "matched_sector": "Plastics",
                "emission_factor": 2.0,
                "ef_source": "CEDA",
                "kg_co2e": 10.0,
                "share_pct": 33.3333,
                "flag_status": "ok",
                "data_source": "secondary",
            },
        ],
    }


def test_apply_primary_data_creates_new_version_without_mutating_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _source_product_with_line_items()
    source_snapshot = {
        "product": dict(source),
        "line_items": [dict(li) for li in source["line_items"]],
    }
    product_inserts: list[dict] = []
    line_item_inserts: list[list[dict]] = []

    def fake_table(name: str) -> MagicMock:
        mock_table = MagicMock()
        if name == "products":
            mock_insert = MagicMock()
            mock_execute = MagicMock()

            def capture_insert(data: dict) -> MagicMock:
                product_inserts.append(data)
                mock_execute.data = [{"product_id": 101}]
                mock_insert.execute = MagicMock(return_value=mock_execute)
                return mock_insert

            mock_table.insert = capture_insert
        elif name == "line_items":
            mock_insert = MagicMock()
            mock_execute = MagicMock()

            def capture_insert(rows: list[dict]) -> MagicMock:
                line_item_inserts.append(rows)
                mock_insert.execute = MagicMock(return_value=mock_execute)
                return mock_insert

            mock_table.insert = capture_insert
        return mock_table

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(store_module, "get_product_by_id", lambda pid, token: source if pid == 5 else None)
    engagement_updates: list[dict] = []
    monkeypatch.setattr(
        store_module,
        "update_engagement",
        lambda engagement_id, *, access_token, **fields: engagement_updates.append(fields),
    )

    result = store_module.apply_primary_data(
        5,
        10,
        8.0,
        "FiberTex email 2025-06-01",
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
        engagement_id=7,
    )

    assert result["new_product_id"] == 101
    assert result["version"] == 2
    assert result["pds_before"] == 0.0
    assert result["pds_after"] == pytest.approx(8.0 / 18.0)

    assert product_inserts[0]["product_lineage_id"] == LINEAGE_A
    assert product_inserts[0]["version"] == 2
    assert product_inserts[0]["status"] == "approved"
    assert product_inserts[0]["total_kg_co2e"] == pytest.approx(18.0)
    assert product_inserts[0]["primary_data_share"] == pytest.approx(8.0 / 18.0)

    primary_row = next(li for li in line_item_inserts[0] if li["component"] == "body")
    assert primary_row["data_source"] == "primary"
    assert primary_row["kg_co2e"] == 8.0
    assert primary_row["emission_factor"] is None
    assert "Supplier primary data" in (primary_row["ef_source"] or "")

    secondary_row = next(li for li in line_item_inserts[0] if li["component"] == "trim")
    assert secondary_row["data_source"] == "secondary"
    assert secondary_row["kg_co2e"] == 10.0

    assert engagement_updates[0]["primary_kg_co2e"] == 8.0
    assert engagement_updates[0]["applied_to_product_id"] == 101

    # Source version remains unchanged (immutability)
    assert source_snapshot["product"]["version"] == 1
    assert source_snapshot["product"]["total_kg_co2e"] == 30.0
    assert source_snapshot["line_items"][0]["data_source"] == "secondary"
