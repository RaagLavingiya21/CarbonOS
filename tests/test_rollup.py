"""Tests for corporate Scope 3 roll-up (Wave 3)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from fastapi.testclient import TestClient

from api.main import app
from calc.rollup import compute_rollup
from db import rollup_store
from tests.conftest import AUTH_HEADERS, TEST_ACCESS_TOKEN, TEST_USER_ID

client = TestClient(app, raise_server_exceptions=False)

LINEAGE_A = str(uuid.uuid4())
LINEAGE_B = str(uuid.uuid4())


def _published_product(
    *,
    product_id: int,
    product_name: str,
    lineage_id: str,
    version: int,
    total_kg_co2e: float = 10.0,
    unitary_product_amount: float = 1.0,
    reporting_period_start: str = "2025-01-01",
    user_id: str = TEST_USER_ID,
) -> dict:
    return {
        "product_id": product_id,
        "user_id": user_id,
        "product_name": product_name,
        "analysis_date": str(date.today()),
        "total_kg_co2e": total_kg_co2e,
        "matched_items": 1,
        "flagged_items": 0,
        "status": "published",
        "product_lineage_id": lineage_id,
        "version": version,
        "unitary_product_amount": unitary_product_amount,
        "reporting_period_start": reporting_period_start,
        "reporting_period_end": "2025-12-31",
        "published_at": "2025-06-01T00:00:00+00:00",
    }


def test_compute_rollup_total_equals_sum_of_contributions() -> None:
    entries = [
        {
            "product_id": 1,
            "product_name": "Alpha",
            "per_unit_kg_co2e": 2.0,
            "annual_volume": 100.0,
        },
        {
            "product_id": 2,
            "product_name": "Beta",
            "per_unit_kg_co2e": 5.0,
            "annual_volume": 50.0,
        },
    ]
    result = compute_rollup(entries)
    assert result["scope3_cat1_total_kg_co2e"] == pytest.approx(450.0)
    assert result["product_count"] == 2
    contributions = [row["contribution_kg_co2e"] for row in result["breakdown"]]
    assert sum(contributions) == pytest.approx(result["scope3_cat1_total_kg_co2e"])


def test_compute_rollup_breakdown_sorted_and_shares_sum_to_100() -> None:
    entries = [
        {
            "product_id": 1,
            "product_name": "Small",
            "per_unit_kg_co2e": 1.0,
            "annual_volume": 10.0,
        },
        {
            "product_id": 2,
            "product_name": "Large",
            "per_unit_kg_co2e": 1.0,
            "annual_volume": 90.0,
        },
    ]
    result = compute_rollup(entries)
    assert result["breakdown"][0]["product_name"] == "Large"
    assert result["breakdown"][1]["product_name"] == "Small"
    share_sum = sum(row["share_pct"] for row in result["breakdown"])
    assert share_sum == pytest.approx(100.0)


def test_compute_rollup_zero_total_has_zero_shares() -> None:
    result = compute_rollup(
        [
            {
                "product_id": 1,
                "product_name": "Zero",
                "per_unit_kg_co2e": 0.0,
                "annual_volume": 100.0,
            }
        ]
    )
    assert result["scope3_cat1_total_kg_co2e"] == 0.0
    assert result["breakdown"][0]["share_pct"] == 0.0


def test_get_rollup_picks_latest_published_per_lineage(monkeypatch: pytest.MonkeyPatch) -> None:
    products = [
        _published_product(
            product_id=1,
            product_name="Widget v1",
            lineage_id=LINEAGE_A,
            version=1,
            total_kg_co2e=10.0,
        ),
        _published_product(
            product_id=2,
            product_name="Widget v2",
            lineage_id=LINEAGE_A,
            version=2,
            total_kg_co2e=20.0,
        ),
    ]

    monkeypatch.setattr(
        rollup_store,
        "get_products_for_active_org",
        lambda access_token, user_id=None, status=None: products if status == "published" else [],
    )

    def fake_table(name: str):
        from unittest.mock import MagicMock

        mock_table = MagicMock()
        if name == "product_volumes":
            mock_execute = MagicMock()
            mock_execute.data = [
                {
                    "volume_id": 1,
                    "product_lineage_id": LINEAGE_A,
                    "user_id": TEST_USER_ID,
                    "year": 2025,
                    "annual_volume": 100.0,
                    "unit": "units",
                    "created_at": "2025-01-01T00:00:00+00:00",
                    "updated_at": "2025-01-01T00:00:00+00:00",
                }
            ]
            mock_table.select.return_value.in_.return_value.eq.return_value.execute.return_value = (
                mock_execute
            )
        return mock_table

    mock_client = type("Client", (), {})()
    mock_client.table = fake_table
    monkeypatch.setattr(rollup_store, "get_user_client", lambda _token: mock_client)

    result = rollup_store.get_rollup(2025, access_token=TEST_ACCESS_TOKEN, user_id=TEST_USER_ID)

    assert result["scope3_cat1_total_kg_co2e"] == pytest.approx(2000.0)
    assert result["product_count"] == 1
    assert result["breakdown"][0]["product_id"] == 2


def test_get_rollup_excludes_other_reporting_years(monkeypatch: pytest.MonkeyPatch) -> None:
    products = [
        _published_product(
            product_id=1,
            product_name="2024 only",
            lineage_id=LINEAGE_A,
            version=1,
            reporting_period_start="2024-01-01",
        ),
    ]

    monkeypatch.setattr(
        rollup_store,
        "get_products_for_active_org",
        lambda access_token, user_id=None, status=None: products if status == "published" else [],
    )
    monkeypatch.setattr(
        rollup_store,
        "get_user_client",
        lambda _token: type("Client", (), {"table": lambda _name: None})(),
    )

    result = rollup_store.get_rollup(2025, access_token=TEST_ACCESS_TOKEN, user_id=TEST_USER_ID)

    assert result["scope3_cat1_total_kg_co2e"] == 0.0
    assert result["product_count"] == 0
    assert result["products_missing_volume"] == []


def test_get_rollup_flags_missing_volume_without_counting_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    products = [
        _published_product(
            product_id=1,
            product_name="No volume product",
            lineage_id=LINEAGE_A,
            version=1,
            total_kg_co2e=15.0,
        ),
    ]

    monkeypatch.setattr(
        rollup_store,
        "get_products_for_active_org",
        lambda access_token, user_id=None, status=None: products if status == "published" else [],
    )

    def fake_table(name: str):
        from unittest.mock import MagicMock

        mock_table = MagicMock()
        if name == "product_volumes":
            mock_execute = MagicMock()
            mock_execute.data = []
            mock_table.select.return_value.in_.return_value.eq.return_value.execute.return_value = (
                mock_execute
            )
        return mock_table

    mock_client = type("Client", (), {})()
    mock_client.table = fake_table
    monkeypatch.setattr(rollup_store, "get_user_client", lambda _token: mock_client)

    result = rollup_store.get_rollup(2025, access_token=TEST_ACCESS_TOKEN, user_id=TEST_USER_ID)

    assert result["scope3_cat1_total_kg_co2e"] == 0.0
    assert result["product_count"] == 0
    assert result["products_missing_volume"] == [
        {"product_id": 1, "product_name": "No volume product"}
    ]


def test_get_rollup_eval_invariant_total_matches_breakdown_sum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    products = [
        _published_product(
            product_id=1,
            product_name="Alpha",
            lineage_id=LINEAGE_A,
            version=1,
            total_kg_co2e=12.0,
            unitary_product_amount=2.0,
        ),
        _published_product(
            product_id=2,
            product_name="Beta",
            lineage_id=LINEAGE_B,
            version=1,
            total_kg_co2e=8.0,
        ),
    ]

    monkeypatch.setattr(
        rollup_store,
        "get_products_for_active_org",
        lambda access_token, user_id=None, status=None: products if status == "published" else [],
    )

    def fake_table(name: str):
        from unittest.mock import MagicMock

        mock_table = MagicMock()
        if name == "product_volumes":
            mock_execute = MagicMock()
            mock_execute.data = [
                {
                    "volume_id": 1,
                    "product_lineage_id": LINEAGE_A,
                    "user_id": TEST_USER_ID,
                    "year": 2025,
                    "annual_volume": 10.0,
                    "unit": "units",
                    "created_at": None,
                    "updated_at": None,
                },
                {
                    "volume_id": 2,
                    "product_lineage_id": LINEAGE_B,
                    "user_id": TEST_USER_ID,
                    "year": 2025,
                    "annual_volume": 5.0,
                    "unit": "units",
                    "created_at": None,
                    "updated_at": None,
                },
            ]
            mock_table.select.return_value.in_.return_value.eq.return_value.execute.return_value = (
                mock_execute
            )
        return mock_table

    mock_client = type("Client", (), {})()
    mock_client.table = fake_table
    monkeypatch.setattr(rollup_store, "get_user_client", lambda _token: mock_client)

    result = rollup_store.get_rollup(2025, access_token=TEST_ACCESS_TOKEN, user_id=TEST_USER_ID)

    breakdown_sum = sum(row["contribution_kg_co2e"] for row in result["breakdown"])
    assert result["scope3_cat1_total_kg_co2e"] == pytest.approx(breakdown_sum)
    assert result["product_count"] == len(result["breakdown"])
    assert {row["product_id"] for row in result["breakdown"]} == {1, 2}


def test_api_get_rollup_returns_total(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.routes.rollup.get_rollup",
        lambda year, access_token, user_id: {
            "scope3_cat1_total_kg_co2e": 300.0,
            "product_count": 1,
            "breakdown": [
                {
                    "product_id": 1,
                    "product_name": "Alpha",
                    "per_unit_kg_co2e": 3.0,
                    "annual_volume": 100.0,
                    "contribution_kg_co2e": 300.0,
                    "share_pct": 100.0,
                }
            ],
            "year": year,
            "products_missing_volume": [],
        },
    )

    response = client.get("/api/rollup?year=2025", headers=AUTH_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope3_cat1_total_kg_co2e"] == 300.0
    assert payload["year"] == 2025


def test_api_put_volume_upserts_and_rejects_negative(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_set_product_volume(product_id, *, year, annual_volume, unit, user_id, access_token):
        captured.update(
            {
                "product_id": product_id,
                "year": year,
                "annual_volume": annual_volume,
                "unit": unit,
                "user_id": user_id,
                "access_token": access_token,
            }
        )
        return {
            "volume_id": 1,
            "product_lineage_id": LINEAGE_A,
            "user_id": user_id,
            "year": year,
            "annual_volume": annual_volume,
            "unit": unit,
            "created_at": "2025-01-01T00:00:00+00:00",
            "updated_at": "2025-01-01T00:00:00+00:00",
        }

    monkeypatch.setattr("api.routes.rollup.set_product_volume", fake_set_product_volume)

    create_response = client.put(
        "/api/analyses/7/volume",
        headers=AUTH_HEADERS,
        json={"year": 2025, "annual_volume": 1000, "unit": "units"},
    )
    assert create_response.status_code == 200
    assert captured["product_id"] == 7
    assert captured["annual_volume"] == 1000
    assert captured["user_id"] == TEST_USER_ID

    update_response = client.put(
        "/api/analyses/7/volume",
        headers=AUTH_HEADERS,
        json={"year": 2025, "annual_volume": 2000, "unit": "units"},
    )
    assert update_response.status_code == 200
    assert captured["annual_volume"] == 2000

    bad_response = client.put(
        "/api/analyses/7/volume",
        headers=AUTH_HEADERS,
        json={"year": 2025, "annual_volume": -1, "unit": "units"},
    )
    assert bad_response.status_code == 422


def test_api_put_volume_returns_404_for_missing_product(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_set_product_volume(*_args, **_kwargs):
        raise ValueError("Product 99 not found.")

    monkeypatch.setattr("api.routes.rollup.set_product_volume", fake_set_product_volume)

    response = client.put(
        "/api/analyses/99/volume",
        headers=AUTH_HEADERS,
        json={"year": 2025, "annual_volume": 10, "unit": "units"},
    )
    assert response.status_code == 404
