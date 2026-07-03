from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import AUTH_HEADERS

# raise_server_exceptions=False so the app's exception handlers produce the
# real HTTP response instead of the TestClient re-raising the exception.
client = TestClient(app, raise_server_exceptions=False)


def test_upstream_connection_timeout_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Supabase connection timeout (httpx.TransportError) becomes a retryable
    503, not a generic 500 - so the frontend can prompt the user to retry."""

    def raise_connect_timeout(*_args: object, **_kwargs: object) -> list[dict]:
        raise httpx.ConnectTimeout("connection to Supabase timed out")

    monkeypatch.setattr(
        "api.routes.analyzer.get_products_for_active_org",
        raise_connect_timeout,
    )

    response = client.get("/api/analyses", headers=AUTH_HEADERS)

    assert response.status_code == 503
    assert "temporarily unreachable" in response.json()["detail"].lower()


def test_non_connection_error_still_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    """A genuine bug (non-transport exception) still surfaces as a 500, so we
    don't mislabel real server errors as transient."""

    def raise_value_error(*_args: object, **_kwargs: object) -> list[dict]:
        raise ValueError("a real bug")

    monkeypatch.setattr(
        "api.routes.analyzer.get_products_for_active_org",
        raise_value_error,
    )

    response = client.get("/api/analyses", headers=AUTH_HEADERS)

    assert response.status_code == 500
    assert "internal server error" in response.json()["detail"].lower()
