"""Unauthenticated public routes (Wave 2).

All endpoints here live under ``/api/public/`` — the only auth bypass prefix.
Access control is enforced in store code via unguessable share tokens and
published-footprint checks, not via JWT.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.models.schemas import CreatePcfRequestRequest, CreatePcfRequestResponse
from db.request_store import create_request
from db.share_store import get_shared_footprint, get_shared_pact_payload

router = APIRouter(tags=["public"])


@router.post("/api/public/pcf-requests", response_model=CreatePcfRequestResponse)
def create_public_pcf_request(body: CreatePcfRequestRequest) -> CreatePcfRequestResponse:
    """Accept an inbound PCF request without authentication (service-client insert)."""
    try:
        request_id = create_request(
            body.org_id,
            requester_name=body.requester_name,
            requester_email=body.requester_email,
            requester_company=body.requester_company,
            product_name=body.product_name,
            message=body.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CreatePcfRequestResponse(request_id=request_id)


@router.get("/api/public/footprints/{share_token}")
def get_public_footprint(share_token: str) -> dict:
    """Read-only footprint view for a valid share token (no JWT required)."""
    view = get_shared_footprint(share_token)
    if view is None:
        raise HTTPException(status_code=404, detail="Shared footprint not found.")
    return view


@router.get("/api/public/footprints/{share_token}/pact")
def get_public_pact(share_token: str) -> dict:
    """PACT v3 ProductFootprint JSON for a valid share token (no JWT required)."""
    try:
        payload = get_shared_pact_payload(share_token)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail="Shared footprint not found.")
    return payload
