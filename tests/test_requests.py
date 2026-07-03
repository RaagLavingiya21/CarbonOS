from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from db import request_store as request_store_module
from tests.conftest import AUTH_HEADERS, TEST_ACCESS_TOKEN, TEST_USER_ID

client = TestClient(app, raise_server_exceptions=False)

ORG_ID = "11111111-1111-1111-1111-111111111111"


def _open_request(**overrides: object) -> dict:
    row = {
        "request_id": 1,
        "org_id": ORG_ID,
        "requester_name": "Alex Analyst",
        "requester_email": "alex@retailer.com",
        "requester_company": "Retailer Co",
        "product_name": "Water bottle",
        "message": "Need PCF for supplier reporting.",
        "status": "open",
        "fulfilled_share_id": None,
        "created_at": "2026-01-01T00:00:00Z",
    }
    row.update(overrides)
    return row


def test_create_request_inserts_open_request(monkeypatch: pytest.MonkeyPatch) -> None:
    inserts: list[dict] = []

    class FakeTable:
        def __init__(self, name: str) -> None:
            self.name = name

        def select(self, *_args: object, **_kwargs: object) -> "FakeTable":
            return self

        def eq(self, *_args: object, **_kwargs: object) -> "FakeTable":
            return self

        def limit(self, *_args: object, **_kwargs: object) -> "FakeTable":
            return self

        def insert(self, row: dict) -> "FakeTable":
            inserts.append(row)
            return self

        def execute(self) -> MagicMock:
            if self.name == "organizations":
                return MagicMock(data=[{"id": ORG_ID}])
            return MagicMock(data=[{"request_id": 42, **inserts[-1]}])

    mock_client = MagicMock()
    mock_client.table.side_effect = lambda name: FakeTable(name)
    monkeypatch.setattr(request_store_module, "get_service_client", lambda: mock_client)

    request_id = request_store_module.create_request(
        ORG_ID,
        requester_name="Alex Analyst",
        requester_email="alex@retailer.com",
        requester_company="Retailer Co",
        product_name="Water bottle",
        message="Need PCF for supplier reporting.",
    )
    assert request_id == 42
    assert inserts[0]["status"] == "open"
    assert inserts[0]["org_id"] == ORG_ID


def test_create_request_rejects_overlong_message(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ValueError, match="message must be at most"):
        request_store_module.create_request(
            ORG_ID,
            requester_name="Alex",
            requester_email="alex@retailer.com",
            requester_company="Retailer Co",
            product_name="Water bottle",
            message="x" * 2001,
        )


def test_list_requests_for_org_is_org_scoped(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeQuery:
        def select(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def eq(self, field: str, value: object) -> "FakeQuery":
            captured["org_id_filter"] = value
            return self

        def order(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def execute(self) -> MagicMock:
            return MagicMock(data=[_open_request()])

    mock_client = MagicMock()
    mock_client.table.return_value = FakeQuery()
    monkeypatch.setattr(request_store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        request_store_module,
        "get_active_org_member_ids",
        lambda access_token, user_id=None: [TEST_USER_ID],
    )
    monkeypatch.setattr(
        request_store_module,
        "get_active_org",
        lambda access_token, user_id=None: MagicMock(id=ORG_ID),
    )

    rows = request_store_module.list_requests_for_org(
        TEST_ACCESS_TOKEN,
        user_id=TEST_USER_ID,
    )
    assert captured["org_id_filter"] == ORG_ID
    assert rows[0]["request_id"] == 1


def test_fulfil_request_requires_published_footprint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        request_store_module,
        "get_active_org",
        lambda access_token, user_id=None: MagicMock(id=ORG_ID),
    )

    class FakeQuery:
        def select(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def eq(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def limit(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def update(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def execute(self) -> MagicMock:
            return MagicMock(data=[_open_request()])

    mock_client = MagicMock()
    mock_client.table.return_value = FakeQuery()
    monkeypatch.setattr(request_store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        request_store_module,
        "get_product_by_id",
        lambda product_id, access_token: {"product_id": product_id, "status": "approved"},
    )

    with pytest.raises(ValueError, match="published"):
        request_store_module.fulfil_request(
            1,
            42,
            user_id=TEST_USER_ID,
            access_token=TEST_ACCESS_TOKEN,
        )


def test_fulfil_request_creates_share_and_marks_fulfilled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    updates: list[dict] = []

    class FakeQuery:
        def select(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def eq(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def limit(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def update(self, data: dict) -> "FakeQuery":
            updates.append(data)
            return self

        def execute(self) -> MagicMock:
            return MagicMock(data=[_open_request()])

    mock_client = MagicMock()
    mock_client.table.return_value = FakeQuery()
    monkeypatch.setattr(request_store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        request_store_module,
        "get_active_org",
        lambda access_token, user_id=None: MagicMock(id=ORG_ID),
    )
    monkeypatch.setattr(
        request_store_module,
        "get_product_by_id",
        lambda product_id, access_token: {
            "product_id": product_id,
            "product_name": "Water bottle",
            "status": "published",
        },
    )
    monkeypatch.setattr(
        request_store_module,
        "create_share",
        lambda product_id, *, recipient_label, user_id, access_token: {
            "share_id": 9,
            "share_token": "share-token-abc",
        },
    )
    monkeypatch.setattr(request_store_module, "append_audit_log", lambda *_args, **_kwargs: None)

    result = request_store_module.fulfil_request(
        1,
        42,
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )
    assert result["status"] == "fulfilled"
    assert result["share_token"] == "share-token-abc"
    assert updates[0]["status"] == "fulfilled"
    assert updates[0]["fulfilled_share_id"] == 9


def test_decline_request_sets_declined(monkeypatch: pytest.MonkeyPatch) -> None:
    updates: list[dict] = []

    class FakeQuery:
        def select(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def eq(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def limit(self, *_args: object, **_kwargs: object) -> "FakeQuery":
            return self

        def update(self, data: dict) -> "FakeQuery":
            updates.append(data)
            return self

        def execute(self) -> MagicMock:
            return MagicMock(data=[_open_request()])

    mock_client = MagicMock()
    mock_client.table.return_value = FakeQuery()
    monkeypatch.setattr(request_store_module, "get_user_client", lambda _token: mock_client)
    monkeypatch.setattr(
        request_store_module,
        "get_active_org",
        lambda access_token, user_id=None: MagicMock(id=ORG_ID),
    )
    monkeypatch.setattr(request_store_module, "append_audit_log", lambda *_args, **_kwargs: None)

    result = request_store_module.decline_request(
        1,
        user_id=TEST_USER_ID,
        access_token=TEST_ACCESS_TOKEN,
    )
    assert result["status"] == "declined"
    assert updates[0]["status"] == "declined"


def test_public_create_request_works_without_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "api.routes.public.create_request",
        lambda *_args, **_kwargs: 7,
    )
    response = client.post(
        "/api/public/pcf-requests",
        json={
            "org_id": ORG_ID,
            "requester_name": "Alex Analyst",
            "requester_email": "alex@retailer.com",
            "requester_company": "Retailer Co",
            "product_name": "Water bottle",
            "message": "Need PCF for supplier reporting.",
        },
    )
    assert response.status_code == 200
    assert response.json()["request_id"] == 7
