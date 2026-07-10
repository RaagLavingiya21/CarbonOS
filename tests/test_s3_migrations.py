"""Migration-hygiene lint for the Scope-3 SQL migrations (band 300-399).

Runs without a database — it parses the .sql text and enforces the tenancy /
re-runnability conventions so the migrations are validated before they are ever
applied:
  - filename number is in the Scope-3 band 300-399,
  - CREATE TABLE IF NOT EXISTS (re-runnable),
  - every table carries `org_id UUID NOT NULL` and enables RLS,
  - RLS uses public.is_org_member(org_id); never shares_org_with; user_id never
    appears inside a USING / WITH CHECK clause,
  - every CREATE POLICY is preceded by a DROP POLICY IF EXISTS of the same name.
"""

from __future__ import annotations

import re
from pathlib import Path

_MIG_DIR = Path(__file__).parent.parent / "supabase" / "migrations"

# Scope-3 reserved migration band: the whole 300-399 block (integrator grant,
# 2026-07-09), chosen high to avoid any collision with the low-numbered scopes.
# The earlier 050-059 assignment was retired — those A/B/C migrations were
# renumbered into 300-309, so Scope 3 now lives in one contiguous band.
_S3_BANDS = ((300, 399),)


def _in_band(num: int) -> bool:
    return any(lo <= num <= hi for lo, hi in _S3_BANDS)


def _s3_migrations() -> list[Path]:
    files = _MIG_DIR.glob("3*.sql")
    return sorted(f for f in files if _in_band(int(f.name[:3])))


def test_scope3_migrations_exist():
    assert _s3_migrations(), "no Scope-3 (300-399) migrations found"


def test_filenames_in_band():
    for p in _s3_migrations():
        num = int(p.name[:3])
        assert _in_band(num), f"{p.name} outside Scope-3 bands {_S3_BANDS}"


def test_tables_are_org_scoped_and_rls_enabled():
    for p in _s3_migrations():
        sql = p.read_text()
        low = sql.lower()
        assert "create table if not exists" in low, f"{p.name}: not re-runnable CREATE TABLE"
        assert re.search(r"org_id\s+uuid\s+not null", low), (
            f"{p.name}: missing org_id UUID NOT NULL"
        )
        assert "enable row level security" in low, f"{p.name}: RLS not enabled"


def test_rls_uses_is_org_member_and_not_user_id():
    for p in _s3_migrations():
        sql = p.read_text()
        assert "is_org_member(org_id)" in sql, f"{p.name}: RLS must use is_org_member(org_id)"
        assert "shares_org_with" not in sql, f"{p.name}: uses deprecated shares_org_with"
        # user_id must never appear inside a policy predicate.
        for line in sql.splitlines():
            if "using (" in line.lower() or "with check (" in line.lower():
                assert "user_id" not in line.lower(), (
                    f"{p.name}: user_id used in an RLS predicate: {line.strip()!r}"
                )


def test_every_create_policy_has_a_preceding_drop():
    for p in _s3_migrations():
        sql = p.read_text()
        created = set(re.findall(r"create policy\s+(\w+)", sql, re.I))
        dropped = set(re.findall(r"drop policy if exists\s+(\w+)", sql, re.I))
        missing = created - dropped
        assert not missing, f"{p.name}: CREATE POLICY without DROP POLICY IF EXISTS: {missing}"
