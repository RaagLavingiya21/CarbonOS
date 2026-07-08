"""Tests for Bayou credentials storage and auth handshake."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from db import s1_bayou_store
from db.s1_bayou_store import NoCredentialsError


@pytest.fixture
def mock_client():
    """Mock Supabase client for credential operations."""
    return MagicMock()


def test_get_or_create_credentials_creates_row_if_missing(mock_client):
    """First access creates an inactive row waiting for API key."""
    # Mock return: no existing row
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    # Mock insert: create empty row
    table_mock.insert.return_value.execute.return_value.data = [{
        "id": "cred1",
        "org_id": "org123",
        "bayou_api_key": "",
        "is_active": False,
        "last_sync": None,
        "next_sync": None,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
    }]
    
    result = s1_bayou_store.get_or_create_credentials(
        "org123", mock_client, access_token="token"
    )
    assert result["org_id"] == "org123"
    assert result["is_active"] is False
    assert result["bayou_api_key"] == ""


def test_get_or_create_credentials_returns_existing_row(mock_client):
    """Returns existing credentials if already configured."""
    # Mock return: existing row
    existing = {
        "id": "cred1",
        "org_id": "org123",
        "bayou_api_key": "key_test",
        "is_active": True,
        "last_sync": "2025-01-01T10:00:00Z",
        "next_sync": "2025-01-01T11:00:00Z",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T10:00:00Z",
    }
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [existing]
    
    result = s1_bayou_store.get_or_create_credentials(
        "org123", mock_client, access_token="token"
    )
    assert result["bayou_api_key"] == "key_test"
    assert result["is_active"] is True


def test_set_api_key_stores_and_activates(mock_client):
    """Setting API key stores it and marks credentials active."""
    table_mock = mock_client.table.return_value
    table_mock.update.return_value.eq.return_value.execute.return_value.data = [{
        "id": "cred1",
        "org_id": "org123",
        "bayou_api_key": "new_key_xyz",
        "is_active": True,
        "last_sync": None,
        "next_sync": None,
        "updated_at": "2025-01-01T00:05:00Z",
        "created_at": "2025-01-01T00:00:00Z",
    }]
    
    result = s1_bayou_store.set_api_key(
        "org123", "new_key_xyz", mock_client, access_token="token"
    )
    assert result["bayou_api_key"] == "new_key_xyz"
    assert result["is_active"] is True
    # Verify update was called with correct params
    table_mock.update.assert_called_once()


def test_get_active_api_key_raises_if_missing(mock_client):
    """get_active_api_key raises NoCredentialsError if not configured."""
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = []
    
    with pytest.raises(NoCredentialsError, match="No active Bayou credentials"):
        s1_bayou_store.get_active_api_key(
            "org123", mock_client, access_token="token"
        )


def test_get_active_api_key_returns_key_if_active(mock_client):
    """get_active_api_key returns the key if active."""
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"bayou_api_key": "live_key_abc123"}
    ]
    
    result = s1_bayou_store.get_active_api_key(
        "org123", mock_client, access_token="token"
    )
    assert result == "live_key_abc123"


def test_mark_sync_complete_updates_timestamps(mock_client):
    """mark_sync_complete sets last_sync and schedules next_sync."""
    table_mock = mock_client.table.return_value
    table_mock.update.return_value.eq.return_value.execute.return_value.data = [{
        "id": "cred1",
        "org_id": "org123",
        "bayou_api_key": "key",
        "is_active": True,
        "last_sync": "2025-01-01T10:00:00+00:00",
        "next_sync": "2025-01-01T11:00:00+00:00",
        "updated_at": "2025-01-01T10:00:00+00:00",
        "created_at": "2025-01-01T00:00:00Z",
    }]
    
    result = s1_bayou_store.mark_sync_complete(
        "org123", mock_client, access_token="token"
    )
    assert result["last_sync"] is not None
    assert result["next_sync"] is not None
    # next_sync should be 1 hour after last_sync
    last_sync = datetime.fromisoformat(result["last_sync"])
    next_sync = datetime.fromisoformat(result["next_sync"])
    delta = (next_sync - last_sync).total_seconds()
    assert 3599 < delta < 3601  # ~3600 seconds (1 hour)


def test_should_sync_returns_false_if_inactive(mock_client):
    """should_sync returns False if credentials are inactive."""
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"is_active": False, "next_sync": None}
    ]
    
    result = s1_bayou_store.should_sync(
        "org123", mock_client, access_token="token"
    )
    assert result is False


def test_should_sync_returns_true_if_never_synced(mock_client):
    """should_sync returns True if next_sync is NULL (never synced)."""
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"is_active": True, "next_sync": None}
    ]
    
    result = s1_bayou_store.should_sync(
        "org123", mock_client, access_token="token"
    )
    assert result is True


def test_should_sync_returns_true_if_past_schedule(mock_client):
    """should_sync returns True if now >= next_sync."""
    now = datetime.now(timezone.utc)
    past_sync = (now - timedelta(hours=2)).isoformat()  # 2 hours ago
    
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"is_active": True, "next_sync": past_sync}
    ]
    
    result = s1_bayou_store.should_sync(
        "org123", mock_client, access_token="token"
    )
    assert result is True


def test_should_sync_returns_false_if_future_schedule(mock_client):
    """should_sync returns False if now < next_sync."""
    now = datetime.now(timezone.utc)
    future_sync = (now + timedelta(hours=2)).isoformat()  # 2 hours from now
    
    table_mock = mock_client.table.return_value
    table_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"is_active": True, "next_sync": future_sync}
    ]
    
    result = s1_bayou_store.should_sync(
        "org123", mock_client, access_token="token"
    )
    assert result is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
