"""API routes for CEDA sector search and emission-factor overrides."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    CreateEFOverrideRequest,
    EFOverrideDTO,
    RemapLineRequest,
    RemapLineResponse,
    SectorOptionDTO,
)
from db.ef_override_store import (
    delete_override,
    list_overrides,
    search_sector_options,
    set_override,
)
from db.reader import get_product_by_id
from db.store import remap_line_item

router = APIRouter(tags=["factors"])


@router.get("/api/factors/sectors", response_model=list[SectorOptionDTO])
def search_sectors_route(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> list[SectorOptionDTO]:
    pairs = search_sector_options(q, limit=limit)
    return [SectorOptionDTO(sector_code=code, sector_name=name) for code, name in pairs]


@router.get("/api/ef-overrides", response_model=list[EFOverrideDTO])
def list_ef_overrides(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[EFOverrideDTO]:
    overrides = list_overrides(current_user.access_token, user_id=current_user.user_id)
    return [EFOverrideDTO.from_domain(row) for row in overrides]


@router.post("/api/ef-overrides", response_model=EFOverrideDTO)
def create_ef_override(
    request: CreateEFOverrideRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> EFOverrideDTO:
    try:
        override = set_override(
            request.material,
            request.sector_code,
            request.sector_name,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return EFOverrideDTO.from_domain(override)


@router.delete("/api/ef-overrides/{override_id}")
def delete_ef_override(
    override_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, bool]:
    try:
        delete_override(
            override_id,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": True}


@router.post("/api/analyses/{product_id}/remap-line", response_model=RemapLineResponse)
def remap_analysis_line(
    product_id: int,
    request: RemapLineRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> RemapLineResponse:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")

    try:
        result = remap_line_item(
            product_id,
            request.item_id,
            request.sector_code,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if request.save_override:
        material = next(
            (
                li.get("material")
                for li in product.get("line_items") or []
                if li.get("item_id") == request.item_id
            ),
            None,
        )
        if material:
            set_override(
                str(material),
                request.sector_code,
                result.get("sector_name"),
                user_id=current_user.user_id,
                access_token=current_user.access_token,
            )

    return RemapLineResponse(**result)
