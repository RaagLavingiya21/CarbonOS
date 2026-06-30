"""FastAPI routes for organization management and membership."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from postgrest.exceptions import APIError

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    AddMemberRequest,
    CreateOrgRequest,
    OrgDetailResponse,
    OrganizationDTO,
    OrgMemberDTO,
    RemoveMemberResponse,
    SetActiveOrgRequest,
)
from db import org_store

router = APIRouter(tags=["organizations"])


def _supabase_error_detail(exc: APIError) -> str:
    message = getattr(exc, "message", None) or str(exc)
    if isinstance(message, dict):
        return str(message.get("message") or message)
    return str(message)


def _require_org_membership(org_id: str, access_token: str):
    orgs = org_store.list_user_orgs(access_token)
    target = next((org for org in orgs if org.id == org_id), None)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=f"Organization '{org_id}' not found.",
        )
    return target


@router.post("/api/orgs", response_model=OrganizationDTO)
def create_org(
    request: CreateOrgRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> OrganizationDTO:
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Organization name cannot be empty.")

    if org_store.user_has_non_demo_org(current_user.access_token):
        raise HTTPException(
            status_code=409,
            detail="You already belong to a personal organization.",
        )

    try:
        org_id = org_store.create_org(name, access_token=current_user.access_token)
        org_store.add_creator_membership(
            current_user.user_id,
            org_id,
            role="admin",
        )
        org = org_store.set_active_org(
            current_user.user_id,
            org_id,
            access_token=current_user.access_token,
        )
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create organization: {_supabase_error_detail(exc)}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return OrganizationDTO.from_domain(org)


@router.get("/api/orgs/mine", response_model=OrgDetailResponse)
def get_my_org(
    current_user: CurrentUser = Depends(get_current_user),
) -> OrgDetailResponse:
    orgs = org_store.list_user_orgs(current_user.access_token)
    active = org_store.get_active_org(
        current_user.access_token,
        user_id=current_user.user_id,
    )
    members: list[OrgMemberDTO] = []
    if active is not None:
        members = [
            OrgMemberDTO.from_domain(member)
            for member in org_store.list_members(active.id, current_user.access_token)
        ]

    return OrgDetailResponse(
        orgs=[OrganizationDTO.from_domain(org) for org in orgs],
        active_org=OrganizationDTO.from_domain(active) if active else None,
        members=members,
    )


@router.patch("/api/orgs/active", response_model=OrganizationDTO)
def set_active_org(
    request: SetActiveOrgRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> OrganizationDTO:
    try:
        org = org_store.set_active_org(
            current_user.user_id,
            request.org_id.strip(),
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to set active organization: {_supabase_error_detail(exc)}",
        ) from exc

    return OrganizationDTO.from_domain(org)


@router.post("/api/orgs/{org_id}/members", response_model=OrgMemberDTO)
def add_member(
    org_id: str,
    request: AddMemberRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> OrgMemberDTO:
    org = _require_org_membership(org_id, current_user.access_token)
    if org.is_demo:
        raise HTTPException(
            status_code=403,
            detail="Cannot add members to the demo organization.",
        )

    email = request.email.strip()
    if not email:
        raise HTTPException(status_code=422, detail="Email cannot be empty.")

    user_id = org_store.find_user_id_by_email(email)
    if user_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"No user found with email '{email}'.",
        )

    org_store.add_member(
        user_id,
        org_id,
        access_token=current_user.access_token,
        role="member",
    )

    members = org_store.list_members(org_id, current_user.access_token)
    added = next((member for member in members if member.user_id == user_id), None)
    if added is None:
        raise HTTPException(status_code=500, detail="Failed to add member.")
    return OrgMemberDTO.from_domain(added)


@router.delete(
    "/api/orgs/{org_id}/members/{user_id}",
    response_model=RemoveMemberResponse,
)
def remove_member(
    org_id: str,
    user_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> RemoveMemberResponse:
    org = _require_org_membership(org_id, current_user.access_token)
    if org.is_demo:
        raise HTTPException(
            status_code=403,
            detail="Cannot remove members from the demo organization.",
        )

    org_store.remove_member(user_id, org_id, access_token=current_user.access_token)
    return RemoveMemberResponse(removed=True)
