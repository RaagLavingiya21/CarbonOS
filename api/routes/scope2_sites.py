"""Scope 2 site-master routes: module health, sector templates, and site CRUD.

All paths live under /api/scope2 and require the same Supabase JWT as the rest of
the platform. Sites are org-scoped (RLS); org_id is resolved via resolve_org_id.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    CreateSiteRequest,
    Scope2HealthResponse,
    SiteDTO,
    SiteTemplateDTO,
    UpdateSiteRequest,
    all_site_template_dtos,
)
from api.routes.scope2_deps import resolve_org_id
from db import s2_site_store
from s2_sites.templates import get_template

router = APIRouter(prefix="/api/scope2", tags=["scope2"])


@router.get("/health", response_model=Scope2HealthResponse)
def scope2_health(
    current_user: CurrentUser = Depends(get_current_user),
) -> Scope2HealthResponse:
    """Liveness check for the Scope 2 module (auth-gated like all module routes)."""
    return Scope2HealthResponse(status="ok")


@router.get("/site-templates", response_model=list[SiteTemplateDTO])
def list_site_templates(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SiteTemplateDTO]:
    """Return the prebuilt consumer-sector site templates (PRD 5.3)."""
    return all_site_template_dtos()


@router.post("/sites", response_model=SiteDTO, status_code=201)
def create_site(
    request: CreateSiteRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SiteDTO:
    org_id = resolve_org_id(current_user)
    # Drop None fields so DB defaults apply (an explicit NULL would violate the
    # NOT NULL columns), then fill boundary fields from the sector template (PRD 5.3).
    payload = request.model_dump(exclude_none=True)
    try:
        template = get_template(request.site_type)
        payload.setdefault("ownership", template.default_ownership)
        payload.setdefault("lease_type", template.default_lease_type)
    except KeyError:
        pass  # unknown site_type falls to the column CHECK/DEFAULT
    site_id = s2_site_store.create_site(
        payload,
        org_id=org_id,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
    )
    row = s2_site_store.get_site(site_id, current_user.access_token)
    if row is None:
        raise HTTPException(status_code=500, detail="Site created but not retrievable.")
    return SiteDTO.from_row(row)


@router.get("/sites", response_model=list[SiteDTO])
def list_sites(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[SiteDTO]:
    rows = s2_site_store.list_sites(current_user.access_token)
    return [SiteDTO.from_row(row) for row in rows]


@router.get("/sites/{site_id}", response_model=SiteDTO)
def get_site(
    site_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> SiteDTO:
    row = s2_site_store.get_site(site_id, current_user.access_token)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return SiteDTO.from_row(row)


@router.patch("/sites/{site_id}", response_model=SiteDTO)
def update_site(
    site_id: int,
    request: UpdateSiteRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SiteDTO:
    existing = s2_site_store.get_site(site_id, current_user.access_token)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    updates = request.model_dump(exclude_none=True)
    row = s2_site_store.update_site(
        site_id, updates, access_token=current_user.access_token
    )
    return SiteDTO.from_row(row or existing)


@router.delete("/sites/{site_id}", status_code=204)
def delete_site(
    site_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    try:
        s2_site_store.delete_site(site_id, access_token=current_user.access_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
