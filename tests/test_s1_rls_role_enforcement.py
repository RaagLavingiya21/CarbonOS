"""Guards for RLS-hard role enforcement (migration 116).

RLS *behaviour* needs a live Postgres + a viewer JWT to verify (see the
ephemeral-user smoke harness); these static checks guard the migration's
correctness so a regression (e.g. a new write policy left on bare is_org_member)
is caught in CI without a DB.
"""

from __future__ import annotations

import pathlib
import re

MIG = (
    pathlib.Path(__file__).resolve().parents[1]
    / "supabase/migrations/116_s1_rls_role_enforcement.sql"
)
SQL = MIG.read_text()

_WRITE_POLICY = re.compile(
    r"CREATE POLICY (\w+) ON (s1_\w+)\s+FOR (INSERT|UPDATE|DELETE)[^;]*;",
    re.IGNORECASE,
)
ADMIN_TABLES = {"s1_member_role", "s1_ef_override"}


def test_helper_functions_defined_security_definer() -> None:
    assert "CREATE OR REPLACE FUNCTION public.s1_can_edit" in SQL
    assert "CREATE OR REPLACE FUNCTION public.s1_is_admin" in SQL
    assert SQL.count("SECURITY DEFINER") >= 2       # mirror is_org_member's pattern


def test_can_edit_denies_viewers_is_admin_checks_admin() -> None:
    # s1_can_edit = org member AND not an explicit viewer
    assert "role = 'viewer'" in SQL and "NOT EXISTS" in SQL
    # s1_is_admin resolves the admin role (explicit or org-admin default)
    assert "role = 'admin'" in SQL


def test_every_write_policy_uses_a_role_helper() -> None:
    policies = _WRITE_POLICY.findall(SQL)
    assert len(policies) >= 50                       # all s1 write policies rewritten
    for block in _WRITE_POLICY.finditer(SQL):
        text = block.group(0)
        assert ("s1_can_edit(org_id)" in text) or ("s1_is_admin(org_id)" in text), text
        assert "is_org_member" not in text           # no bare org-membership write check


def test_admin_tables_gated_by_is_admin() -> None:
    for block in _WRITE_POLICY.finditer(SQL):
        _, table, _ = block.groups()
        if table in ADMIN_TABLES:
            assert "s1_is_admin(org_id)" in block.group(0)
        else:
            assert "s1_can_edit(org_id)" in block.group(0)


def test_drop_create_balanced() -> None:
    drops = len(re.findall(r"^DROP POLICY IF EXISTS", SQL, re.MULTILINE))
    creates = len(re.findall(r"^CREATE POLICY", SQL, re.MULTILINE))
    assert drops == creates and creates >= 50


def test_no_select_policies_touched() -> None:
    # viewers keep read access — this migration only rewrites write policies
    assert "FOR SELECT" not in SQL
