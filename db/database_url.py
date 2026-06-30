"""Normalize DATABASE_URL for Postgres drivers (LangGraph checkpointer)."""

from __future__ import annotations

import os


def get_database_url() -> str | None:
    """Return a clean Postgres URI, or None if unset/invalid.

    Railway/dashboard copies sometimes include trailing comments such as
    "(direct connection string from Supabase, port 5432)" — psycopg rejects
    spaces in URIs. We keep only the leading postgresql://... token.
    """
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return None
    if raw.startswith(("postgresql://", "postgres://")):
        return raw.split()[0]
    return None
