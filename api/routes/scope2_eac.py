"""Scope 2 EAC registry routes — RECs/GOs/green tariffs/PPAs (PRD 5.4; V1).

CRUD over the contractual instruments that back market-based accounting. Instruments
are org-scoped (RLS) and consumed by the calc engine, which screens each against the
8 GHG Protocol quality criteria before it can cover load.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import CreateEac, EacDTO
from api.routes.scope2_deps import resolve_org_id
from db import s2_eac_store, s2_site_store

router = APIRouter(prefix="/api/scope2", tags=["scope2"])


@router.get("/eacs", response_model=list[EacDTO])
def list_eacs(current_user: CurrentUser = Depends(get_current_user)) -> list[EacDTO]:
    return [EacDTO.from_row(row) for row in s2_eac_store.list_eacs(current_user.access_token)]


@router.post("/eacs", response_model=EacDTO, status_code=201)
def create_eac(
    request: CreateEac,
    current_user: CurrentUser = Depends(get_current_user),
) -> EacDTO:
    org_id = resolve_org_id(current_user)
    token = current_user.access_token

    if s2_site_store.get_site(request.site_id, token) is None:
        raise HTTPException(status_code=404, detail=f"Site {request.site_id} not found.")

    instrument_id = s2_eac_store.create_eac(
        request.model_dump(exclude_none=True),
        org_id=org_id,
        user_id=current_user.user_id,
        access_token=token,
    )
    row = s2_eac_store.get_eac(instrument_id, token)
    if row is None:
        raise HTTPException(status_code=500, detail="EAC created but not retrievable.")
    return EacDTO.from_row(row)


@router.delete("/eacs/{instrument_id}", status_code=204)
def delete_eac(
    instrument_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> None:
    s2_eac_store.delete_eac(instrument_id, access_token=current_user.access_token)
