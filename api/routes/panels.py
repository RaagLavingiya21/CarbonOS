"""FastAPI routes for active module panel persistence."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    ActivePanelDTO,
    CreatePanelRequest,
    DeletePanelResponse,
    UpdatePanelRequest,
)
from db import panel_store

router = APIRouter(tags=["panels"])


def _panel_or_404(panel_id: str, access_token: str):
    panel = panel_store.get_panel(panel_id, access_token)
    if panel is None:
        raise HTTPException(
            status_code=404,
            detail=f"Panel '{panel_id}' not found.",
        )
    return panel


@router.get("/api/panels", response_model=list[ActivePanelDTO])
def list_panels(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[ActivePanelDTO]:
    panels = panel_store.list_panels(current_user.access_token)
    return [ActivePanelDTO.from_domain(panel) for panel in panels]


@router.post("/api/panels", response_model=ActivePanelDTO)
def create_panel(
    request: CreatePanelRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ActivePanelDTO:
    module_type = request.module_type.strip()
    if not module_type:
        raise HTTPException(status_code=422, detail="module_type cannot be empty.")

    panel_id = panel_store.create_panel(
        module_type,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
        thread_id=request.thread_id,
        panel_state=request.panel_state,
        tab_order=request.tab_order,
        is_active=request.is_active,
    )
    panel = _panel_or_404(panel_id, current_user.access_token)
    return ActivePanelDTO.from_domain(panel)


@router.patch("/api/panels/{panel_id}", response_model=ActivePanelDTO)
def update_panel(
    panel_id: str,
    request: UpdatePanelRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ActivePanelDTO:
    _panel_or_404(panel_id, current_user.access_token)

    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields provided to update.")

    panel_store.update_panel(panel_id, access_token=current_user.access_token, **updates)
    panel = _panel_or_404(panel_id, current_user.access_token)
    return ActivePanelDTO.from_domain(panel)


@router.delete("/api/panels/{panel_id}", response_model=DeletePanelResponse)
def delete_panel(
    panel_id: str,
    current_user: CurrentUser = Depends(get_current_user),
) -> DeletePanelResponse:
    _panel_or_404(panel_id, current_user.access_token)
    panel_store.delete_panel(panel_id, access_token=current_user.access_token)
    return DeletePanelResponse(deleted=True)
