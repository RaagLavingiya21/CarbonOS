"""Scope 2 site-master routes.

Phase 0 exposes a module health check and the read-only sector site-template
catalog (real data from s2_sites.templates). Site CRUD, ingestion, landlord
workflow, calc, and reporting routers land in later phases. All paths live under
/api/scope2 and require the same Supabase JWT as the rest of the platform.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    Scope2HealthResponse,
    SiteTemplateDTO,
    all_site_template_dtos,
)

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
