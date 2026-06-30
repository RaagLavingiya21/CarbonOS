"""Supabase CRUD for platform chat agent organizations and membership.

Tables (managed by supabase/migrations/):
  organizations — team / org records
  org_members   — user membership in an org

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from dataclasses import dataclass

from db.client import get_user_client

_ORG_COLUMNS = "id, name, created_at"
_MEMBER_COLUMNS = "user_id, org_id, role"


@dataclass
class Organization:
    id: str
    name: str
    created_at: str


@dataclass
class OrgMember:
    user_id: str
    org_id: str
    role: str


def create_org(name: str, *, access_token: str) -> str:
    """Insert an organization and return its id.

    Caller should add the creator via add_member() before they can SELECT the org (RLS).
    """
    client = get_user_client(access_token)
    response = (
        client.table("organizations")
        .insert({"name": name.strip()})
        .execute()
    )
    return str(response.data[0]["id"])


def add_member(
    user_id: str,
    org_id: str,
    *,
    access_token: str,
    role: str = "member",
) -> None:
    """Add a user to an org (idempotent upsert on primary key)."""
    client = get_user_client(access_token)
    client.table("org_members").upsert(
        {
            "user_id": user_id,
            "org_id": org_id,
            "role": role,
        }
    ).execute()


def remove_member(user_id: str, org_id: str, *, access_token: str) -> None:
    """Remove a user from an org."""
    client = get_user_client(access_token)
    client.table("org_members").delete().eq("user_id", user_id).eq(
        "org_id", org_id
    ).execute()


def get_user_org(access_token: str) -> Organization | None:
    """Return the first organization the authenticated user belongs to."""
    client = get_user_client(access_token)
    membership_response = (
        client.table("org_members")
        .select("org_id")
        .limit(1)
        .execute()
    )
    if not membership_response.data:
        return None

    org_id = str(membership_response.data[0]["org_id"])
    org_response = (
        client.table("organizations")
        .select(_ORG_COLUMNS)
        .eq("id", org_id)
        .limit(1)
        .execute()
    )
    if not org_response.data:
        return None
    return _organization_from_row(org_response.data[0])


def list_members(org_id: str, access_token: str) -> list[OrgMember]:
    """Return all members of an organization."""
    client = get_user_client(access_token)
    response = (
        client.table("org_members")
        .select(_MEMBER_COLUMNS)
        .eq("org_id", org_id)
        .execute()
    )
    return [_member_from_row(row) for row in response.data]


def _organization_from_row(row: dict) -> Organization:
    return Organization(
        id=str(row["id"]),
        name=row["name"],
        created_at=str(row.get("created_at", "")),
    )


def _member_from_row(row: dict) -> OrgMember:
    return OrgMember(
        user_id=str(row["user_id"]),
        org_id=str(row["org_id"]),
        role=row.get("role", "member"),
    )
