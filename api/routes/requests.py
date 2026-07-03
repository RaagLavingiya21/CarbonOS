"""Authenticated routes for the PCF request inbox."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    DeclinePcfRequestResponse,
    FulfilPcfRequestRequest,
    FulfilPcfRequestResponse,
    PcfRequestDTO,
)
from db.request_store import decline_request, fulfil_request, list_requests_for_org

router = APIRouter(tags=["pcf-requests"])


@router.get("/api/pcf-requests", response_model=list[PcfRequestDTO])
def list_pcf_requests(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[PcfRequestDTO]:
    rows = list_requests_for_org(current_user.access_token, user_id=current_user.user_id)
    return [PcfRequestDTO.model_validate(row) for row in rows]


@router.post(
    "/api/pcf-requests/{request_id}/fulfil",
    response_model=FulfilPcfRequestResponse,
)
def fulfil_pcf_request_route(
    request_id: int,
    body: FulfilPcfRequestRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> FulfilPcfRequestResponse:
    try:
        result = fulfil_request(
            request_id,
            body.product_id,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "published" in message.lower() or "not open" in message.lower() else 404
        raise HTTPException(status_code=status_code, detail=message) from exc
    return FulfilPcfRequestResponse(**result)


@router.post(
    "/api/pcf-requests/{request_id}/decline",
    response_model=DeclinePcfRequestResponse,
)
def decline_pcf_request_route(
    request_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> DeclinePcfRequestResponse:
    try:
        result = decline_request(
            request_id,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if "not open" in message.lower() else 404
        raise HTTPException(status_code=status_code, detail=message) from exc
    return DeclinePcfRequestResponse(**result)
