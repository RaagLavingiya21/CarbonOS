"""FastAPI routes for supplier engagement copilot workflows."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

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
from copilot.draft_email import run as draft_email
from copilot.exception_router import run as route_exception
from copilot.parse_response import run as parse_response
from copilot.suppliers_list import run as get_suppliers_list
from db.copilot_store import (
    append_audit_log,
    create_engagement,
    get_audit_log,
    get_engagement,
    init_copilot_db,
    update_engagement,
)

router = APIRouter(tags=["supplier-copilot"])


_STATUS_BY_ACTION = {
    "store_data": "closed",
    "draft_follow_up": "follow-up",
    "flag_for_human_review": "flagged",
    "escalate": "flagged",
}


def _days_since_created(created_at: str | None) -> int:
    if not created_at:
        return 0
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return 0
    return max((datetime.now() - created).days, 0)


@router.get("/api/copilot/suppliers", response_model=SuppliersListResponse)
def suppliers(product_name: str, top_n: int = Query(10, ge=1, le=100)) -> SuppliersListResponse:
    result = get_suppliers_list(product_name, top_n=top_n)
    return SuppliersListResponse.from_domain(result)


@router.post("/api/copilot/draft-email", response_model=DraftEmailResponse)
def draft_supplier_email(request: DraftEmailRequest) -> DraftEmailResponse:
    session_id = request.session_id or str(uuid4())
    result = draft_email(
        request.candidate.to_domain(),
        request.product_name,
        session_id=session_id,
    )
    dto = EmailDraftResultDTO.from_domain(result)
    return DraftEmailResponse(session_id=session_id, **dto.model_dump())


@router.post("/api/copilot/engagements", response_model=CreateEngagementsResponse)
def create_supplier_engagements(request: CreateEngagementsRequest) -> CreateEngagementsResponse:
    init_copilot_db()
    engagement_ids: dict[str, int] = {}
    for item in request.engagements:
        engagement_id = create_engagement(
            supplier_name=item.supplier_name,
            product_name=request.product_name,
            component_name=item.component,
            material=item.material,
            kg_co2e=item.kg_co2e,
            share_pct=item.share_pct,
            email_draft=item.email_body,
        )
        engagement_ids[item.supplier_name] = engagement_id
        append_audit_log(
            event="email_drafted",
            workflow="draft_email",
            supplier_name=item.supplier_name,
            product_name=request.product_name,
            component_name=item.component,
            email_sent=item.email_body,
            status="open",
        )
    return CreateEngagementsResponse(engagement_ids=engagement_ids)


@router.post("/api/copilot/route-response", response_model=RouteResponseResponse)
def route_supplier_response(request: RouteResponseRequest) -> RouteResponseResponse:
    engagement = get_engagement(request.engagement_id)
    if engagement is None:
        raise HTTPException(
            status_code=404,
            detail=f"Engagement {request.engagement_id} not found.",
        )

    parse_result = parse_response(
        response_text=request.response_text,
        supplier_name=request.supplier_name,
        component=request.component or engagement.component_name,
        session_id=request.session_id,
    )
    if parse_result.error or parse_result.parsed is None:
        return RouteResponseResponse(
            parsed=ParseResponseResultDTO.from_domain(parse_result),
            routing=None,
            engagement_status=engagement.status,
        )

    route_result = route_exception(
        parsed=parse_result.parsed,
        supplier_name=request.supplier_name,
        component=request.component or engagement.component_name,
        days_since_contact=_days_since_created(engagement.created_at),
        session_id=request.session_id,
    )
    decision = route_result.decision
    new_status = _STATUS_BY_ACTION.get(decision.action if decision else "", "flagged")

    update_engagement(
        request.engagement_id,
        status=new_status,
        response_received=request.response_text,
        routing_decision=decision.action if decision else None,
        decision_rationale=decision.rationale if decision else None,
        ghg_protocol_citation=decision.ghg_protocol_citation if decision else None,
        next_step=decision.action if decision else None,
    )
    append_audit_log(
        event="response_parsed_and_routed",
        workflow="parse_response+exception_router",
        supplier_name=request.supplier_name,
        product_name=engagement.product_name,
        component_name=request.component or engagement.component_name,
        email_sent=engagement.email_draft,
        response_received=request.response_text,
        routing_decision=decision.action if decision else None,
        decision_rationale=decision.rationale if decision else None,
        ghg_protocol_citation=decision.ghg_protocol_citation if decision else None,
        data_collected=parse_result.parsed.data_provided,
        status=new_status,
    )
    return RouteResponseResponse(
        parsed=ParseResponseResultDTO.from_domain(parse_result),
        routing=RoutingResultDTO.from_domain(route_result),
        engagement_status=new_status,
    )


@router.get("/api/copilot/audit-log", response_model=list[AuditEntryDTO])
def audit_log(
    supplier_name: str | None = None,
    product_name: str | None = None,
) -> list[AuditEntryDTO]:
    return [
        AuditEntryDTO.from_domain(entry)
        for entry in get_audit_log(supplier_name=supplier_name, product_name=product_name)
    ]


@router.get("/api/copilot/audit-log/export")
def export_audit_log(
    supplier_name: str | None = None,
    product_name: str | None = None,
) -> StreamingResponse:
    entries = get_audit_log(supplier_name=supplier_name, product_name=product_name)
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
