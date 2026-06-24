from __future__ import annotations

import pytest

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_ACCESS_TOKEN = "test-access-token"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"}


@pytest.fixture(autouse=True)
def bypass_supabase_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass JWT verification in API tests."""

    def fake_verify(_token: str) -> str:
        return TEST_USER_ID

    monkeypatch.setattr("api.middleware.auth.verify_supabase_jwt", fake_verify)
