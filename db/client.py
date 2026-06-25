"""Supabase client factory for Postgres-backed persistence."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def _require_config() -> tuple[str, str]:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set. "
            "See .env.example for required Supabase configuration."
        )
    return SUPABASE_URL, SUPABASE_ANON_KEY


@lru_cache(maxsize=1)
def get_service_client() -> Client:
    """Service-role client for admin operations (bypasses RLS). Use sparingly."""
    url, _ = _require_config()
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY must be set for service-role access.")
    return create_client(url, SUPABASE_SERVICE_ROLE_KEY)


def get_user_client(access_token: str) -> Client:
    """User-scoped client; RLS policies apply via the caller's JWT."""
    url, anon_key = _require_config()
    client = create_client(url, anon_key)
    client.postgrest.auth(access_token)
    return client
