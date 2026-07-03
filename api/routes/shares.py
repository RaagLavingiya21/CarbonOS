"""Authenticated routes for footprint share links."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    CreateShareRequest,
    CreateShareResponse,
    RevokeShareResponse,
    ShareSummaryDTO,
)
from db.share_store import create_share, list_shares_for_product, revoke_share

router = APIRouter(tags=["shares"])


@router.post(
    "/api/analyses/{product_id}/shares",
    response_model=CreateShareResponse,
)
def create_share_route(
    product_id: int,
    request: CreateShareRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CreateShareResponse:
    try:
        result = create_share(
            product_id,
            recipient_label=request.recipient_label,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        message = str(exc)
        if "published" in message.lower():
            raise HTTPException(status_code=409, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return CreateShareResponse(**result)


@router.get(
    "/api/analyses/{product_id}/shares",
    response_model=list[ShareSummaryDTO],
)
def list_shares_route(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[ShareSummaryDTO]:
    try:
        shares = list_shares_for_product(product_id, current_user.access_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [ShareSummaryDTO.model_validate(row) for row in shares]


@router.delete(
    "/api/shares/{share_id}",
    response_model=RevokeShareResponse,
)
def revoke_share_route(
    share_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> RevokeShareResponse:
    try:
        result = revoke_share(
            share_id,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RevokeShareResponse(**result)
