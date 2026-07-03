from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest
from fastapi.testclient import TestClient

from api.main import app
from db import share_store as share_store_module
from exchange.pact import build_product_footprint
from tests.conftest import AUTH_HEADERS, TEST_ACCESS_TOKEN, TEST_USER_ID

client = TestClient(app, raise_server_exceptions=False)
SCHEMA_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "pact_v3_product_footprint_schema.json"
)


def _published_product(**overrides: object) -> dict:
    product = {
        "product_id": 42,
        "user_id": TEST_USER_ID,
        "product_name": "Shared Product",
        "product_description": "A published footprint",
        "analysis_date": "2025-06-15",
        "total_kg_co2e": 12.5,
        "matched_items": 5,
        "flagged_items": 0,
        "status": "published",
        "footprint_uuid": str(uuid4()),
        "declared_unit": "piece",
        "unitary_product_amount": 1.0,
        "system_boundary": "cradle-to-gate",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "geography_country": "US",
        "primary_data_share": 0.25,
        "spec_version": "3.0.0",
        "version": 2,
        "product_lineage_id": str(uuid4()),
        "published_at": "2025-06-20T00:00:00Z",
        "technological_dqr": 2,
        "geographical_dqr": 3,
        "temporal_dqr": 1,
        "dqr_computed_at": "2025-06-15T10:00:00Z",
        "submitted_for_review_by": "00000000-0000-0000-0000-000000000099",
        "submitted_at": "2025-06-18T00:00:00Z",
        "reviewed_by": "00000000-0000-0000-0000-000000000098",
        "reviewed_at": "2025-06-20T00:00:00Z",
        "review_comment": None,
        "created_at": "2025-06-15T10:00:00Z",
        "updated_at": "2025-06-20T00:00:00Z",
        "line_items": [
            {
                "item_id": 1,
                "user_id": TEST_USER_ID,
                "component": "body",
                "material": "cotton",
                "spend_usd": 4.0,
                "matched_sector": "Cotton",
                "emission_factor": 1.5,
                "ef_source": "Open CEDA 2025",
                "kg_co2e": 10.0,
                "share_pct": 80.0,
                "flag_status": "matched",
                "data_source": "secondary",
                "ef_confidence": 92.0,
                "country_of_origin": "US",
                "technological_dqr": 2,
                "geographical_dqr": 3,
                "temporal_dqr": 1,
            }
        ],
    }
    product.update(overrides)
    return product


def test_create_share_rejects_non_published(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        share_store_module,
        "get_product_by_id",
        lambda product_id, access_token: _published_product(status="approved"),
    )
    with pytest.raises(ValueError, match="published"):
        share_store_module.create_share(
            42,
            recipient_label="Partner",
            user_id=TEST_USER_ID,
            access_token=TEST_ACCESS_TOKEN,
        )


def test_create_share_route_returns_409_for_non_published(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_not_published(*_args: object, **_kwargs: object) -> dict:
        raise ValueError("Only published footprints can be shared.")

    monkeypatch.setattr("api.routes.shares.create_share", raise_not_published)
    response = client.post(
        "/api/analyses/42/shares",
        headers=AUTH_HEADERS,
        json={"recipient_label": "Partner"},
    )
    assert response.status_code == 409
    assert "published" in response.json()["detail"].lower()


def test_get_shared_footprint_returns_view_for_valid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = _published_product()
    monkeypatch.setattr(
        share_store_module,
        "_resolve_active_share",
        lambda share_token: ({"share_token": share_token}, product),
    )
    monkeypatch.setattr(
        share_store_module,
        "_build_public_provenance",
        lambda _product: {
            "product_name": "Shared Product",
            "total_kg_co2e": 12.5,
            "matched_items": 5,
            "flagged_items": 0,
            "metadata": {"status": "published"},
            "method_statement": {"summary": "Spend-based", "detail": "Screening-grade"},
            "primary_data_share": 0.25,
            "aggregate_dqr": {},
            "line_items": product["line_items"],
            "version_lineage": [],
        },
    )

    view = share_store_module.get_shared_footprint("valid-token")
    assert view is not None
    assert view["product_name"] == "Shared Product"
    assert view["total_kg_co2e"] == 12.5
    assert len(view["line_items"]) == 1


def test_get_shared_footprint_returns_none_when_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(share_store_module, "_resolve_active_share", lambda _token: None)
    assert share_store_module.get_shared_footprint("bad-token") is None


def test_get_shared_footprint_returns_none_for_revoked_share(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(share_store_module, "_resolve_active_share", lambda _token: None)
    assert share_store_module.get_shared_footprint("revoked-token") is None


def test_public_view_omits_user_id(monkeypatch: pytest.MonkeyPatch) -> None:
    product = _published_product()
    monkeypatch.setattr(
        share_store_module,
        "_resolve_active_share",
        lambda share_token: ({"share_token": share_token}, product),
    )
    monkeypatch.setattr(
        share_store_module,
        "_build_public_provenance",
        lambda _product: {
            "product_name": "Shared Product",
            "user_id": TEST_USER_ID,
            "metadata": {"submitted_for_review_by": TEST_USER_ID},
            "line_items": product["line_items"],
            "version_lineage": [],
            "method_statement": {"summary": "Spend-based", "detail": "Screening-grade"},
            "primary_data_share": 0.25,
            "aggregate_dqr": {},
            "total_kg_co2e": 12.5,
            "matched_items": 5,
            "flagged_items": 0,
        },
    )

    view = share_store_module.get_shared_footprint("valid-token")
    assert view is not None
    serialized = json.dumps(view)
    assert "user_id" not in serialized
    assert TEST_USER_ID not in serialized
    assert "submitted_for_review_by" not in serialized
    assert "reviewed_by" not in serialized


def test_public_pact_validates_against_vendored_schema(
    monkeypatch: pytest.MonkeyPatch,
    pact_schema: dict,
) -> None:
    product = _published_product()
    monkeypatch.setattr(
        share_store_module,
        "_resolve_active_share",
        lambda share_token: ({"share_token": share_token}, product),
    )
    monkeypatch.setattr(
        share_store_module,
        "_org_context_for_product_owner",
        lambda _owner: ("Acme Corp", "org-123"),
    )

    payload = share_store_module.get_shared_pact_payload("valid-token")
    assert payload is not None
    jsonschema.validate(instance=payload, schema=pact_schema)


@pytest.fixture
def pact_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def test_public_footprint_endpoint_reachable_without_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    view = share_store_module._strip_owner_fields(
        {
            "product_name": "Shared Product",
            "total_kg_co2e": 12.5,
            "matched_items": 5,
            "flagged_items": 0,
            "metadata": {"status": "published"},
            "method_statement": {"summary": "Spend-based", "detail": "Screening-grade"},
            "primary_data_share": 0.0,
            "aggregate_dqr": {},
            "line_items": [],
            "version_lineage": [],
        }
    )
    monkeypatch.setattr("api.routes.public.get_shared_footprint", lambda _token: view)

    response = client.get("/api/public/footprints/public-share-token")
    assert response.status_code == 200
    assert response.json()["product_name"] == "Shared Product"


def test_public_footprint_endpoint_returns_404_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("api.routes.public.get_shared_footprint", lambda _token: None)
    response = client.get("/api/public/footprints/missing-token")
    assert response.status_code == 404


def test_public_pact_endpoint_reachable_without_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    product = _published_product()
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")
    monkeypatch.setattr("api.routes.public.get_shared_pact_payload", lambda _token: payload)

    response = client.get("/api/public/footprints/public-share-token/pact")
    assert response.status_code == 200
    assert response.json()["productNameCompany"] == "Shared Product"
