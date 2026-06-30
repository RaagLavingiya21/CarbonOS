"""Supabase CRUD for platform chat agent organizations and membership.

Tables (managed by supabase/migrations/):
  organizations — team / org records
  org_members   — user membership in an org
  user_preferences — active workspace per user

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from db.client import get_service_client, get_user_client

_ORG_COLUMNS = "id, name, created_at, is_demo"
_MEMBER_COLUMNS = "user_id, org_id, role"


@dataclass
class Organization:
    id: str
    name: str
    created_at: str
    is_demo: bool = False


@dataclass
class OrgMember:
    user_id: str
    org_id: str
    role: str


def demo_org_id() -> str | None:
    value = os.getenv("DEMO_ORG_ID", "").strip()
    return value or None


def _users_from_list_response(response: object) -> list:
    """Normalize list_users() result (SDK returns a list, not {users: [...]})."""
    if isinstance(response, list):
        return response
    users = getattr(response, "users", None)
    if isinstance(users, list):
        return users
    return []


def find_user_id_by_email(email: str) -> str | None:
    """Resolve a Supabase Auth user id from email (service-role admin lookup)."""
    normalized = email.strip().lower()
    if not normalized:
        return None

    client = get_service_client()
    page = 1
    per_page = 200

    while True:
        response = client.auth.admin.list_users(page=page, per_page=per_page)
        users = _users_from_list_response(response)
        if not users:
            return None

        for user in users:
            user_email = getattr(user, "email", None)
            if user_email and user_email.strip().lower() == normalized:
                return str(user.id)

        if len(users) < per_page:
            return None
        page += 1


def ensure_demo_membership(user_id: str) -> None:
    """Idempotently add user to the configured demo org (service role)."""
    org_id = demo_org_id()
    if not org_id:
        return

    client = get_service_client()
    client.table("org_members").upsert(
        {"user_id": user_id, "org_id": org_id, "role": "demo_member"},
        returning="minimal",
    ).execute()


def create_org(name: str, *, access_token: str) -> str:
    """Insert an organization and return its id.

    Caller should add the creator via add_creator_membership() before they can SELECT the org (RLS).
    Uses returning='minimal' because SELECT on organizations requires org membership.
    """
    client = get_user_client(access_token)
    org_id = str(uuid.uuid4())
    (
        client.table("organizations")
        .insert({"id": org_id, "name": name.strip(), "is_demo": False}, returning="minimal")
        .execute()
    )
    return org_id


def add_creator_membership(user_id: str, org_id: str, *, role: str = "admin") -> None:
    """Add the org creator as the first member (service role bypasses RLS bootstrap)."""
    client = get_service_client()
    client.table("org_members").insert(
        {"user_id": user_id, "org_id": org_id, "role": role},
        returning="minimal",
    ).execute()


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
        },
        returning="minimal",
    ).execute()


def remove_member(user_id: str, org_id: str, *, access_token: str) -> None:
    """Remove a user from an org."""
    client = get_user_client(access_token)
    client.table("org_members").delete().eq("user_id", user_id).eq(
        "org_id", org_id
    ).execute()


def list_user_orgs(access_token: str) -> list[Organization]:
    """Return all organizations the authenticated user belongs to."""
    client = get_user_client(access_token)
    membership_response = client.table("org_members").select("org_id").execute()
    if not membership_response.data:
        return []

    org_ids = [str(row["org_id"]) for row in membership_response.data]
    org_response = (
        client.table("organizations")
        .select(_ORG_COLUMNS)
        .in_("id", org_ids)
        .execute()
    )
    orgs = [_organization_from_row(row) for row in org_response.data]
    orgs.sort(key=lambda org: (org.is_demo, org.name.lower()))
    return orgs


def get_user_org(access_token: str) -> Organization | None:
    """Return the active organization for the authenticated user."""
    return get_active_org(access_token)


def get_active_org(access_token: str, *, user_id: str | None = None) -> Organization | None:
    """Return the user's active workspace org, with sensible defaults."""
    orgs = list_user_orgs(access_token)
    if not orgs:
        return None

    if user_id is None:
        client = get_user_client(access_token)
        pref_response = (
            client.table("user_preferences")
            .select("active_org_id")
            .limit(1)
            .execute()
        )
        if pref_response.data and pref_response.data[0].get("active_org_id"):
            active_id = str(pref_response.data[0]["active_org_id"])
            for org in orgs:
                if org.id == active_id:
                    return org

    non_demo = [org for org in orgs if not org.is_demo]
    if non_demo:
        return non_demo[0]

    demo = [org for org in orgs if org.is_demo]
    return demo[0] if demo else orgs[0]


def get_active_org_member_ids(access_token: str, *, user_id: str | None = None) -> list[str]:
    """Return user ids for members of the active org (for product scoping)."""
    org = get_active_org(access_token, user_id=user_id)
    if org is None:
        return []
    members = list_members(org.id, access_token)
    return [member.user_id for member in members]


def set_active_org(user_id: str, org_id: str, *, access_token: str) -> Organization:
    """Set the user's active workspace; org_id must be a membership they hold."""
    orgs = list_user_orgs(access_token)
    target = next((org for org in orgs if org.id == org_id), None)
    if target is None:
        raise ValueError(f"User is not a member of organization '{org_id}'.")

    client = get_user_client(access_token)
    client.table("user_preferences").upsert(
        {"user_id": user_id, "active_org_id": org_id},
        returning="minimal",
    ).execute()
    return target


def user_has_non_demo_org(access_token: str) -> bool:
    """True if the user belongs to at least one non-demo organization."""
    return any(not org.is_demo for org in list_user_orgs(access_token))


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
        is_demo=bool(row.get("is_demo", False)),
    )


def _member_from_row(row: dict) -> OrgMember:
    return OrgMember(
        user_id=str(row["user_id"]),
        org_id=str(row["org_id"]),
        role=row.get("role", "member"),
    )
