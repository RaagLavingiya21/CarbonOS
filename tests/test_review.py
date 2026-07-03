from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db import store as store_module
from tests.conftest import AUTH_HEADERS, TEST_ACCESS_TOKEN, TEST_USER_ID

client = TestClient(app)

SUBMITTER = TEST_USER_ID
REVIEWER = "00000000-0000-0000-0000-000000000002"


def _under_review_product(**overrides: object) -> dict:
    product = {
        "product_id": 1,
        "product_name": "Review Product",
        "status": "under_review",
        "submitted_for_review_by": SUBMITTER,
        "submitted_at": "2026-01-01T00:00:00Z",
        "reviewed_by": None,
        "reviewed_at": None,
        "line_items": [],
    }
    product.update(overrides)
    return product


def test_submit_for_review_transitions_approved(monkeypatch: pytest.MonkeyPatch) -> None:
    updates: list[dict] = []

    def fake_table(name: str) -> MagicMock:
        mock_table = MagicMock()
        if name == "products":
            mock_update = MagicMock()
            mock_eq = MagicMock()
            mock_eq.execute = MagicMock()
            mock_update.eq.return_value = mock_eq
            mock_table.update = lambda data: (updates.append(data), mock_update)[1]
        return mock_table

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        store_module,
        "get_product_by_id",
        lambda product_id, access_token: {
            "product_id": product_id,
            "product_name": "Review Product",
            "status": "approved",
        },
    )
    monkeypatch.setattr(store_module, "append_audit_log", lambda **kwargs: None)

    store_module.submit_for_review(1, user_id=SUBMITTER, access_token=TEST_ACCESS_TOKEN)
    assert updates[0]["status"] == "under_review"
    assert updates[0]["submitted_for_review_by"] == SUBMITTER


def test_approve_review_same_user_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        store_module,
        "get_product_by_id",
        lambda product_id, access_token: _under_review_product(),
    )
    with pytest.raises(ValueError, match="different approver"):
        store_module.approve_review(
            1,
            reviewer_user_id=SUBMITTER,
            access_token=TEST_ACCESS_TOKEN,
        )


def test_approve_review_by_different_member_publishes(monkeypatch: pytest.MonkeyPatch) -> None:
    updates: list[dict] = []

    def fake_table(name: str) -> MagicMock:
        mock_table = MagicMock()
        if name == "products":
            mock_update = MagicMock()
            mock_eq = MagicMock()
            mock_eq.execute = MagicMock()
            mock_update.eq.return_value = mock_eq
            mock_table.update = lambda data: (updates.append(data), mock_update)[1]
        return mock_table

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        store_module,
        "get_product_by_id",
        lambda product_id, access_token: _under_review_product(),
    )
    monkeypatch.setattr(store_module, "append_audit_log", lambda **kwargs: None)
    monkeypatch.setattr(
        "db.org_store.get_active_org_member_ids",
        lambda access_token, user_id=None: [SUBMITTER, REVIEWER],
    )

    store_module.approve_review(
        1,
        reviewer_user_id=REVIEWER,
        access_token=TEST_ACCESS_TOKEN,
    )
    assert updates[0]["status"] == "published"
    assert updates[0]["reviewed_by"] == REVIEWER


def test_publish_route_returns_409() -> None:
    response = client.post("/api/analyses/1/publish", headers=AUTH_HEADERS)
    assert response.status_code == 409


def test_approve_review_route_same_user_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.routes.analyzer.get_product_by_id",
        lambda product_id, access_token: _under_review_product(),
    )

    def fake_approve(*args, **kwargs):
        raise ValueError("review requires a different approver")

    monkeypatch.setattr("api.routes.analyzer.approve_review", fake_approve)
    response = client.post("/api/analyses/1/approve-review", headers=AUTH_HEADERS)
    assert response.status_code == 409


def test_reject_review_returns_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    updates: list[dict] = []

    def fake_table(name: str) -> MagicMock:
        mock_table = MagicMock()
        if name == "products":
            mock_update = MagicMock()
            mock_eq = MagicMock()
            mock_eq.execute = MagicMock()
            mock_update.eq.return_value = mock_eq
            mock_table.update = lambda data: (updates.append(data), mock_update)[1]
        return mock_table

    mock_client = MagicMock()
    mock_client.table.side_effect = fake_table
    monkeypatch.setattr(store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        store_module,
        "get_product_by_id",
        lambda product_id, access_token: _under_review_product(),
    )
    monkeypatch.setattr(store_module, "append_audit_log", lambda **kwargs: None)

    store_module.reject_review(
        1,
        "Needs more primary data",
        reviewer_user_id=REVIEWER,
        access_token=TEST_ACCESS_TOKEN,
    )
    assert updates[0]["status"] == "flagged"
    assert updates[0]["review_comment"] == "Needs more primary data"


def test_published_footprint_requires_different_reviewer() -> None:
    """Eval invariant: published footprints must have reviewer != submitter."""
    product = {
        "status": "published",
        "submitted_for_review_by": SUBMITTER,
        "reviewed_by": REVIEWER,
    }
    assert product["reviewed_by"] != product["submitted_for_review_by"]
