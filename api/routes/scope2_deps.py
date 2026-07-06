"""Shared dependencies for Scope 2 routes.

Resolves the caller's active organization id (shared tenancy infra, same role as
auth) so Scope 2 stores can stamp org_id. Route layer only — Scope 2 business
modules never import org_store.
"""

from __future__ import annotations

from fastapi import HTTPException

from api.middleware.auth import CurrentUser
from db import org_store


def resolve_org_id(current_user: CurrentUser) -> str:
    """Return the caller's active org id, or 400 if they have none."""
    org = org_store.get_active_org(
        current_user.access_token, user_id=current_user.user_id
    )
    if org is None:
        raise HTTPException(
            status_code=400,
            detail="No active organization for this user. Create or join one first.",
        )
    return org.id
