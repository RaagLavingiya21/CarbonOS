"""FastAPI routes for supplier engagement copilot workflows."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from api.middleware.auth import CurrentUser, get_current_user
from fastapi.responses import StreamingResponse

from api.graphs.supplier_copilot_graph import start_email_draft, start_response_routing
from api.models.schemas import (
    AuditEntryDTO,
    CreateEngagementsRequest,
    CreateEngagementsResponse,
    DraftEmailRequest,
    DraftEmailResponse,
    EmailDraftResultDTO,
    ParseResponseResultDTO,
    RouteResponseRequest,
    RouteResponseResponse,
    RoutingResultDTO,
    SuppliersListResponse,
)
from copilot.suppliers_list import run as get_suppliers_list
from db.copilot_store import (
    append_audit_log,
    create_engagement,
    get_audit_log,
    get_engagement,
)

router = APIRouter(tags=["supplier-copilot"])


def _days_since_created(created_at: str | None) -> int:
    if not created_at:
        return 0
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return 0
    return max((datetime.now() - created).days, 0)


@router.get("/api/copilot/suppliers", response_model=SuppliersListResponse)
def suppliers(
    product_name: str,
    top_n: int = Query(10, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
) -> SuppliersListResponse:
    result = get_suppliers_list(
        product_name,
        top_n=top_n,
        access_token=current_user.access_token,
    )
    return SuppliersListResponse.from_domain(result)


@router.post("/api/copilot/draft-email", response_model=DraftEmailResponse)
def draft_supplier_email(
    request: DraftEmailRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> DraftEmailResponse:
    session_id = request.session_id or str(uuid4())
    state = start_email_draft(
        session_id=session_id,
        product_name=request.product_name,
        candidate=request.candidate.to_domain(),
        user_id=current_user.user_id,
        access_token=current_user.access_token,
    )
    draft_result = state.get("email_draft_result")
    if draft_result is None:
        return DraftEmailResponse(
            session_id=session_id,
            draft=None,
            citations=[],
            error="Email draft graph did not produce a result.",
        )
    dto = EmailDraftResultDTO.from_domain(draft_result)
    return DraftEmailResponse(session_id=session_id, **dto.model_dump())


@router.post("/api/copilot/engagements", response_model=CreateEngagementsResponse)
def create_supplier_engagements(
    request: CreateEngagementsRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CreateEngagementsResponse:
    engagement_ids: dict[str, int] = {}
    for item in request.engagements:
        engagement_id = create_engagement(
            supplier_name=item.supplier_name,
            product_name=request.product_name,
            component_name=item.component,
            material=item.material,
            kg_co2e=item.kg_co2e,
            share_pct=item.share_pct,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
            email_draft=item.email_body,
        )
        engagement_ids[item.supplier_name] = engagement_id
        append_audit_log(
            event="email_drafted",
            workflow="draft_email",
            user_id=current_user.user_id,
            access_token=current_user.access_token,
            supplier_name=item.supplier_name,
            product_name=request.product_name,
            component_name=item.component,
            email_sent=item.email_body,
            status="open",
        )
    return CreateEngagementsResponse(engagement_ids=engagement_ids)


@router.post("/api/copilot/route-response", response_model=RouteResponseResponse)
def route_supplier_response(
    request: RouteResponseRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> RouteResponseResponse:
    engagement = get_engagement(request.engagement_id, current_user.access_token)
    if engagement is None:
        raise HTTPException(
            status_code=404,
            detail=f"Engagement {request.engagement_id} not found.",
        )

    session_id = request.session_id or str(uuid4())
    state = start_response_routing(
        session_id=session_id,
        engagement_id=request.engagement_id,
        supplier_name=request.supplier_name,
        response_text=request.response_text,
        component=request.component or engagement.component_name,
        days_since_contact=_days_since_created(engagement.created_at),
        auto_apply=True,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
    )

    parse_result = state.get("parse_result")
    routing_result = state.get("routing_result")

    if parse_result is None:
        return RouteResponseResponse(
            parsed=ParseResponseResultDTO(parsed=None, error="No parse result from routing graph."),
            routing=None,
            engagement_status=engagement.status,
        )

    if parse_result.error or parse_result.parsed is None:
        return RouteResponseResponse(
            parsed=ParseResponseResultDTO.from_domain(parse_result),
            routing=None,
            engagement_status=engagement.status,
        )

    new_status = state.get("engagement_status") or engagement.status
    return RouteResponseResponse(
        parsed=ParseResponseResultDTO.from_domain(parse_result),
        routing=RoutingResultDTO.from_domain(routing_result) if routing_result else None,
        engagement_status=new_status,
    )


@router.get("/api/copilot/audit-log", response_model=list[AuditEntryDTO])
def audit_log(
    supplier_name: str | None = None,
    product_name: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AuditEntryDTO]:
    return [
        AuditEntryDTO.from_domain(entry)
        for entry in get_audit_log(
            current_user.access_token,
            supplier_name=supplier_name,
            product_name=product_name,
        )
    ]


@router.get("/api/copilot/audit-log/export")
def export_audit_log(
    supplier_name: str | None = None,
    product_name: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    entries = get_audit_log(
        current_user.access_token,
        supplier_name=supplier_name,
        product_name=product_name,
    )
    rows = [AuditEntryDTO.from_domain(entry).model_dump() for entry in entries]
    output = io.StringIO()
    fieldnames = list(AuditEntryDTO.model_fields)
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    filename = "supplier_engagement_audit.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
