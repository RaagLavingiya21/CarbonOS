"""Authenticated routes for corporate Scope 3 roll-up and product volumes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    ProductVolumeDTO,
    RollupResponseDTO,
    SetProductVolumeRequest,
)
from db.reader import get_product_by_id
from db.rollup_store import get_product_volume, get_rollup, set_product_volume

router = APIRouter(tags=["rollup"])


@router.get("/api/rollup", response_model=RollupResponseDTO)
def fetch_rollup(
    year: int | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> RollupResponseDTO:
    reporting_year = year if year is not None else date.today().year
    result = get_rollup(
        reporting_year,
        access_token=current_user.access_token,
        user_id=current_user.user_id,
    )
    return RollupResponseDTO(**result)


@router.get("/api/analyses/{product_id}/volume", response_model=ProductVolumeDTO | None)
def fetch_product_volume(
    product_id: int,
    year: int | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> ProductVolumeDTO | None:
    reporting_year = year if year is not None else date.today().year
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    try:
        row = get_product_volume(
            product_id,
            year=reporting_year,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        message = str(exc)
        if "Not authorized" in message:
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    if row is None:
        return None
    return ProductVolumeDTO(**row)


@router.put("/api/analyses/{product_id}/volume", response_model=ProductVolumeDTO)
def update_product_volume(
    product_id: int,
    request: SetProductVolumeRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ProductVolumeDTO:
    try:
        row = set_product_volume(
            product_id,
            year=request.year,
            annual_volume=request.annual_volume,
            unit=request.unit,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        message = str(exc)
        if "annual_volume" in message:
            raise HTTPException(status_code=422, detail=message) from exc
        if "Not authorized" in message:
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return ProductVolumeDTO(**row)
