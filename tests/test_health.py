from __future__ import annotations

from datetime import date

from calc.health import footprint_health


def _product(**overrides: object) -> dict:
    row = {
        "product_id": 1,
        "status": "approved",
        "flagged_items": 0,
        "primary_data_share": 0.5,
        "reporting_period_end": f"{date.today().year}-12-31",
        "technological_dqr": 2,
        "geographical_dqr": 2,
        "temporal_dqr": 1,
    }
    row.update(overrides)
    return row


def test_footprint_health_healthy() -> None:
    result = footprint_health(_product())
    assert result["status"] == "healthy"
    assert result["reasons"] == []


def test_footprint_health_stale_by_reporting_year() -> None:
    result = footprint_health(_product(reporting_period_end="2020-12-31"))
    assert result["status"] == "stale"
    assert any("2020" in reason for reason in result["reasons"])


def test_footprint_health_attention_for_flags_and_zero_pds() -> None:
    result = footprint_health(
        _product(status="flagged", flagged_items=2, primary_data_share=0.0)
    )
    assert result["status"] == "attention"
    assert len(result["reasons"]) >= 2


def test_footprint_health_attention_for_high_dqr() -> None:
    result = footprint_health(
        _product(technological_dqr=4, geographical_dqr=2, temporal_dqr=2)
    )
    assert result["status"] == "attention"
    assert any("technological DQR" in reason for reason in result["reasons"])


def test_portfolio_summary_includes_health_counts(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from api.main import app
    from tests.conftest import AUTH_HEADERS

    products = [
        {
            "product_id": 1,
            "product_name": "Healthy",
            "analysis_date": "2025-01-01",
            "total_kg_co2e": 10.0,
            "matched_items": 1,
            "flagged_items": 0,
            "status": "approved",
            "primary_data_share": 0.5,
            "reporting_period_end": f"{date.today().year}-12-31",
            "technological_dqr": 2,
            "geographical_dqr": 2,
            "temporal_dqr": 1,
        },
        {
            "product_id": 2,
            "product_name": "Stale",
            "analysis_date": "2020-01-01",
            "total_kg_co2e": 5.0,
            "matched_items": 1,
            "flagged_items": 0,
            "status": "approved",
            "primary_data_share": 0.0,
            "reporting_period_end": "2020-12-31",
            "technological_dqr": 4,
            "geographical_dqr": 4,
            "temporal_dqr": 4,
        },
    ]

    monkeypatch.setattr(
        "api.routes.analyzer.get_products_for_active_org",
        lambda access_token, user_id=None, status=None: products,
    )

    client = TestClient(app)
    response = client.get("/api/analyses/summary", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert "counts_by_health" in body
    assert body["counts_by_health"]["healthy"] == 1
    assert body["counts_by_health"]["stale"] == 1
    assert body["needs_attention_count"] == 1
