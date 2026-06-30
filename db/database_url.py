"""Normalize DATABASE_URL for Postgres drivers (LangGraph checkpointer)."""

from __future__ import annotations

import os
from urllib.parse import urlparse


def get_database_url() -> str | None:
    """Return a clean Postgres URI, or None if unset/invalid.

    Railway/dashboard copies sometimes include trailing comments such as
    "(direct connection string from Supabase, port 5432)" — psycopg rejects
    spaces in URIs. We keep only the leading postgresql://... token and
    validate the hostname before connecting.
    """
    raw = os.getenv("DATABASE_URL", "").strip()
    if not raw:
        return None

    if (raw.startswith('"') and raw.endswith('"')) or (
        raw.startswith("'") and raw.endswith("'")
    ):
        raw = raw[1:-1].strip()

    if not raw.startswith(("postgresql://", "postgres://")):
        return None

    url = raw.split()[0]
    host = urlparse(url).hostname
    if not host or host.startswith(".") or ".." in host:
        raise ValueError(_invalid_database_url_message())

    return url


def _invalid_database_url_message() -> str:
    return (
        "DATABASE_URL is malformed (missing or invalid hostname). "
        "In Supabase go to Project Settings → Database → Connection string, "
        "choose URI, use port 5432, and paste the full string into Railway. "
        "It should look like postgresql://postgres.[ref]:[password]@"
        "aws-0-[region].pooler.supabase.com:5432/postgres — no quotes, "
        "no comments, and URL-encode special characters in the password."
    )
