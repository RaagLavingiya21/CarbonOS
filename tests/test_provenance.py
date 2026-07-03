from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from exchange.provenance import build_provenance_markdown
from tests.conftest import AUTH_HEADERS

client = TestClient(app)

SAMPLE_PROVENANCE = {
    "product_id": 1,
    "metadata": {
        "product_name": "Test Product",
        "declared_unit": "piece",
        "system_boundary": "cradle-to-gate",
        "geography_country": "US",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
    },
    "method_statement": {
        "summary": "Spend-based Open CEDA 2025 screening assessment.",
        "detail": "Cradle-to-gate Scope 3 Category 1.",
    },
    "primary_data_share": 0.0,
    "aggregate_dqr": {"technological": 2, "geographical": 4, "temporal": 1},
    "line_items": [
        {
            "component": "body",
            "material": "cotton",
            "matched_sector": "Cotton",
            "emission_factor": 1.5,
            "kg_co2e": 10.0,
            "ef_source": "Open CEDA 2025",
            "ef_confidence": 92.0,
            "data_source": "secondary",
            "technological_dqr": 2,
            "geographical_dqr": 4,
            "temporal_dqr": 1,
        }
    ],
    "version_lineage": [
        {"product_id": 1, "version": 1, "status": "approved", "analysis_date": "2025-06-01"},
    ],
}


def test_provenance_markdown_contains_method_statement() -> None:
    text = build_provenance_markdown(SAMPLE_PROVENANCE)
    assert "Spend-based Open CEDA 2025" in text
    assert "Open CEDA 2025" in text
    assert "Version lineage" in text


def test_provenance_endpoint_404(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.analyzer.get_footprint_provenance",
        lambda product_id, access_token: None,
    )
    response = client.get("/api/footprints/999/provenance", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_provenance_endpoint_json(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.analyzer.get_footprint_provenance",
        lambda product_id, access_token: SAMPLE_PROVENANCE,
    )
    response = client.get("/api/footprints/1/provenance", headers=AUTH_HEADERS)
    assert response.status_code == 200
    body = response.json()
    assert body["line_items"][0]["ef_source"] == "Open CEDA 2025"
    assert body["line_items"][0]["technological_dqr"] == 2
    assert len(body["version_lineage"]) == 1


def test_provenance_endpoint_markdown(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.analyzer.get_footprint_provenance",
        lambda product_id, access_token: SAMPLE_PROVENANCE,
    )
    response = client.get(
        "/api/footprints/1/provenance?format=markdown",
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert "Spend-based Open CEDA 2025" in response.text
