"""FastAPI routes for the Scope 1 module (isolated under /api/scope1).

Thin orchestration: validate -> call business logic (s1_calc / s1_consolidation /
s1_reporting) -> persist via db.scope1_store (RLS-scoped). No calculations inline.
"""

from __future__ import annotations

import base64
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from api.graphs.scope1_ocr_graph import get_ocr_state, review_ocr, start_ocr
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope1_schemas import (
    AssignOwnerRequest,
    CollectionStatusRequest,
    ConsolidationPreviewRequest,
    ConsolidationPreviewResponse,
    CreateDataOwnerRequest,
    CreateEntityRequest,
    CreateFacilityRequest,
    CreateInventoryRequest,
    CreateSourceRequest,
    ExcludeSourceRequest,
    FacilityBreakdownDTO,
    GasBreakdownDTO,
    InventoryReportResponse,
    InviteMemberRequest,
    MobileRecordRequest,
    OcrReviewRequest,
    OnboardingResponse,
    OnboardingStepDTO,
    ReadinessResponse,
    SetBaseYearRequest,
    SetRoleRequest,
    StationaryRecordRequest,
    UpsertBoundaryRequest,
)
from db import org_store
from db import scope1_store as store
from db.scope1_store import NoActiveOrgError
from s1_calc import GasMasses, calculate_mobile, calculate_stationary
from s1_consolidation import compute_consolidation_multiplier
from s1_factors import EmissionFactorLibrary, MissingEmissionFactor
from s1_intake import parse_base_year_csv, parse_intake_csv
from s1_intake.bayou import BayouClient, BayouError, bayou_bill_to_extraction
from s1_onboarding import OnboardingCounts, build_onboarding
from s1_reporting import (
    DisclosureMeta,
    ReportRecord,
    build_inventory_report,
    build_pdf,
    build_xlsx,
    trace_record,
)

router = APIRouter(prefix="/api/scope1", tags=["scope1"])

_COMPLETE_STATUSES = {"received", "entered", "verified"}


def _library() -> EmissionFactorLibrary:
    """Canonical EPA library (mirrors the seeded s1_ef_record reference data)."""
    return EmissionFactorLibrary.default()


def _guard(func, *args, **kwargs):
    """Run a store call, mapping the no-active-org case to a 400."""
    try:
        return func(*args, **kwargs)
    except NoActiveOrgError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# --- Role enforcement (app-layer; RLS handles org tenancy) ------------------

_ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2}


def require_scope1_role(min_role: str):
    """Dependency: 403 unless the caller's resolved Scope-1 role >= min_role."""
    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        role = _guard(store.get_scope1_role, access_token=user.access_token, user_id=user.user_id)
        if _ROLE_RANK.get(role, 0) < _ROLE_RANK[min_role]:
            raise HTTPException(
                status_code=403,
                detail=f"Requires Scope 1 '{min_role}' role (you are '{role}').",
            )
        return user
    return _dependency


require_editor = require_scope1_role("editor")
require_admin = require_scope1_role("admin")


# --- Members & roles --------------------------------------------------------

@router.get("/members")
def list_members(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Org members with their resolved Scope-1 role, plus the caller's own role."""
    members = _guard(store.list_member_roles, access_token=user.access_token, user_id=user.user_id)
    your_role = _guard(store.get_scope1_role, access_token=user.access_token, user_id=user.user_id)
    return {
        "your_role": your_role,
        "members": [{**m, "is_you": m["user_id"] == user.user_id} for m in members],
    }


@router.post("/members/{member_id}/role")
def update_member_role(
    member_id: str, req: SetRoleRequest, user: CurrentUser = Depends(require_admin)
) -> dict:
    if req.role not in _ROLE_RANK:
        raise HTTPException(status_code=422, detail="role must be admin, editor, or viewer.")
    return _guard(store.set_member_role, member_id, req.role,
                  access_token=user.access_token, user_id=user.user_id)


@router.post("/members/invite")
def invite_member(req: InviteMemberRequest, user: CurrentUser = Depends(require_admin)) -> dict:
    """Add a user to the org (reusing the platform invite) and set their Scope-1 role."""
    if req.role not in _ROLE_RANK:
        raise HTTPException(status_code=422, detail="role must be admin, editor, or viewer.")
    target_id = org_store.find_user_id_by_email(req.email)
    if target_id is None:
        raise HTTPException(status_code=404, detail=f"No user found with email '{req.email}'.")
    org = org_store.get_active_org(user.access_token, user_id=user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization.")
    org_store.add_member(target_id, org.id, access_token=user.access_token, role="member")
    return _guard(store.set_member_role, target_id, req.role,
                  access_token=user.access_token, user_id=user.user_id)


# --- Entities / facilities / data owners ------------------------------------

@router.post("/entities")
def create_entity(req: CreateEntityRequest, user: CurrentUser = Depends(require_editor)) -> dict:
    return _guard(store.create_entity, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/entities")
def list_entities(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_entities, access_token=user.access_token, user_id=user.user_id)


@router.post("/facilities")
def create_facility(
    req: CreateFacilityRequest, user: CurrentUser = Depends(require_editor)
) -> dict:
    return _guard(store.create_facility, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/facilities")
def list_facilities(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_facilities, access_token=user.access_token, user_id=user.user_id)


@router.post("/data-owners")
def create_data_owner(
    req: CreateDataOwnerRequest, user: CurrentUser = Depends(require_editor)
) -> dict:
    return _guard(store.create_data_owner, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/data-owners")
def list_data_owners(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_data_owners, access_token=user.access_token, user_id=user.user_id)


@router.post("/sources/{source_id}/assign-owner")
def assign_owner(source_id: str, req: AssignOwnerRequest,
                 user: CurrentUser = Depends(require_editor)) -> dict:
    return _guard(store.assign_source_owner, source_id, req.data_owner_id,
                  access_token=user.access_token, user_id=user.user_id)


# --- Inventory + consolidation ----------------------------------------------

@router.post("/inventories")
def create_inventory(
    req: CreateInventoryRequest, user: CurrentUser = Depends(require_editor)
) -> dict:
    return _guard(store.create_inventory, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/inventories")
def list_inventories(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_inventories, access_token=user.access_token, user_id=user.user_id)


@router.post("/inventories/{inventory_id}/lock")
def lock_inventory(inventory_id: str, user: CurrentUser = Depends(require_editor)) -> dict:
    inv = _guard(store.lock_inventory, inventory_id,
                 access_token=user.access_token, user_id=user.user_id)
    _log(inventory_id, "lock", user, entity_table="s1_inventory")
    return inv


def _apply_base_year(inventory_id: str, base_year: int, total: float, gwp: str,
                     evidence_id: str | None, user: CurrentUser) -> dict:
    inv = _guard(
        store.set_base_year, inventory_id,
        {"base_year": base_year, "base_year_total_tco2e": total, "base_year_gwp_version": gwp},
        access_token=user.access_token, user_id=user.user_id,
    )
    _log(inventory_id, "set_base_year", user, entity_table="s1_inventory",
         field_changes={"base_year": base_year, "total_tco2e": total,
                        "gwp_version": gwp, "evidence_document_id": evidence_id})
    return inv


@router.post("/inventories/{inventory_id}/base-year")
def set_base_year(inventory_id: str, req: SetBaseYearRequest,
                  user: CurrentUser = Depends(require_editor)) -> dict:
    """Set the base year + prior-year total on an inventory (manual entry)."""
    return _apply_base_year(inventory_id, req.base_year, req.base_year_total_tco2e,
                            req.base_year_gwp_version, req.evidence_document_id, user)


@router.post("/inventories/{inventory_id}/base-year/import")
async def import_base_year(
    inventory_id: str, file: UploadFile = File(...),
    user: CurrentUser = Depends(require_editor),
) -> dict:
    """Import a prior-year inventory total from a consultant/spreadsheet CSV
    (columns base_year, total_tco2e, gwp_version?); keeps the file as evidence."""
    data = await file.read()
    parsed = parse_base_year_csv(data)
    if not parsed.is_valid:
        raise HTTPException(status_code=422, detail="; ".join(parsed.errors) or "Invalid base-year CSV.")
    evidence = _guard(
        store.upload_evidence, data, file_name=file.filename or "base-year.csv",
        content_type=file.content_type, document_type="base_year_import",
        inventory_id=inventory_id, access_token=user.access_token, user_id=user.user_id,
    )
    inv = _apply_base_year(inventory_id, parsed.base_year, parsed.total_tco2e,
                           parsed.gwp_version, evidence["id"], user)
    return {**inv, "evidence_document_id": evidence["id"],
            "imported": {"base_year": parsed.base_year, "total_tco2e": parsed.total_tco2e,
                         "gwp_version": parsed.gwp_version}}


@router.post("/consolidation/preview", response_model=ConsolidationPreviewResponse)
def consolidation_preview(req: ConsolidationPreviewRequest) -> ConsolidationPreviewResponse:
    """Pure preview of the consolidation multiplier — no persistence."""
    try:
        result = compute_consolidation_multiplier(
            req.approach,
            equity_pct=req.equity_pct,
            economic_interest_pct=req.economic_interest_pct,
            has_financial_control=req.has_financial_control,
            has_operational_control=req.has_operational_control,
            entity_type=req.entity_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ConsolidationPreviewResponse(multiplier=result.multiplier, rationale=result.rationale)


@router.post("/boundary")
def upsert_boundary(
    req: UpsertBoundaryRequest, user: CurrentUser = Depends(require_editor)
) -> dict:
    """Compute the entity's multiplier from the inventory approach + control flags,
    then store it."""
    inv = _guard(store.get_inventory, req.inventory_id,
                 access_token=user.access_token, user_id=user.user_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    entity = _guard(store.get_entity, req.entity_id,
                    access_token=user.access_token, user_id=user.user_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    result = compute_consolidation_multiplier(
        inv["consolidation_approach"],
        equity_pct=entity.get("equity_pct"),
        economic_interest_pct=entity.get("economic_interest_pct"),
        has_financial_control=entity.get("has_financial_control", False),
        has_operational_control=entity.get("has_operational_control", False),
        entity_type=entity.get("entity_type"),
    )
    row = {
        "inventory_id": req.inventory_id,
        "entity_id": req.entity_id,
        "in_scope": req.in_scope,
        "exclusion_reason": req.exclusion_reason,
        "applied_equity_pct": entity.get("economic_interest_pct") or entity.get("equity_pct"),
        "consolidation_multiplier": result.multiplier,
        "consolidation_rationale": result.rationale,
    }
    return _guard(store.upsert_boundary, row,
                  access_token=user.access_token, user_id=user.user_id)


# --- Sources ----------------------------------------------------------------

@router.post("/sources")
def create_source(req: CreateSourceRequest, user: CurrentUser = Depends(require_editor)) -> dict:
    return _guard(store.create_source, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


@router.get("/sources")
def list_sources(user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_sources, access_token=user.access_token, user_id=user.user_id)


@router.post("/sources/{source_id}/exclude")
def exclude_source(source_id: str, req: ExcludeSourceRequest,
                   user: CurrentUser = Depends(require_editor)) -> dict:
    src = _guard(store.exclude_source, source_id, req.rationale,
                 access_token=user.access_token, user_id=user.user_id)
    _log(source_id, "exclude", user, entity_table="s1_emission_source",
         field_changes={"rationale": req.rationale})
    return src


# --- Intake (records) -------------------------------------------------------

@router.post("/records/stationary")
def create_stationary_record(req: StationaryRecordRequest,
                             user: CurrentUser = Depends(require_editor)) -> dict:
    try:
        return _persist_stationary(req, user)
    except MissingEmissionFactor as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/records/mobile")
def create_mobile_record(req: MobileRecordRequest,
                         user: CurrentUser = Depends(require_editor)) -> dict:
    try:
        return _persist_mobile(req, user)
    except (MissingEmissionFactor, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/records/csv")
async def create_records_csv(
    inventory_id: str = Form(...),
    file: UploadFile = File(...),
    user: CurrentUser = Depends(require_editor),
) -> dict:
    """Bulk-create records from a CSV. Each row is calculated + persisted with
    evidence-less Tier data; row-level errors are reported without aborting."""
    inv = _guard(store.get_inventory, inventory_id,
                 access_token=user.access_token, user_id=user.user_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")

    parsed = parse_intake_csv(await file.read())
    sources = {s["source_name"]: s for s in _guard(
        store.list_sources, access_token=user.access_token, user_id=user.user_id)}

    created: list[str] = []
    row_errors: list[dict] = []
    for r in parsed.rows:
        if not r.is_valid:
            row_errors.append({"row": r.row_index, "errors": r.errors})
            continue
        src = sources.get(r.source_name)
        if src is None:
            row_errors.append({"row": r.row_index, "errors": [f"unknown source '{r.source_name}'"]})
            continue
        try:
            record = _persist_csv_row(r, src["id"], inv, user)
            created.append(record["id"])
        except (MissingEmissionFactor, ValueError) as exc:
            row_errors.append({"row": r.row_index, "errors": [str(exc)]})

    return {
        "created": len(created),
        "record_ids": created,
        "row_errors": row_errors,
        "file_errors": parsed.file_errors,
    }


# --- Evidence + audit trail -------------------------------------------------

@router.post("/evidence")
async def upload_evidence(
    file: UploadFile = File(...),
    inventory_id: str | None = Form(None),
    document_type: str = Form("manual_note"),
    user: CurrentUser = Depends(require_editor),
) -> dict:
    """Upload a source document: SHA-256 computed server-side, bytes stored in the
    private s1-evidence bucket. Returns the evidence id to attach to a record."""
    data = await file.read()
    return _guard(
        store.upload_evidence, data,
        file_name=file.filename or "evidence",
        content_type=file.content_type,
        document_type=document_type,
        inventory_id=inventory_id,
        access_token=user.access_token, user_id=user.user_id,
    )


@router.get("/records/{record_id}/audit")
def record_audit(record_id: str, user: CurrentUser = Depends(get_current_user)) -> list[dict]:
    return _guard(store.list_change_log, "s1_emission_record", record_id,
                  access_token=user.access_token, user_id=user.user_id)


# --- OCR review queue (LangGraph extraction + human review) -----------------

@router.post("/ocr/extract")
async def ocr_extract(
    file: UploadFile = File(...),
    doc_kind: str = Form("utility_bill"),
    inventory_id: str = Form(...),
    parser: str = Form("claude"),          # claude (Vision-LLM) | bayou (trained parser)
    user: CurrentUser = Depends(require_editor),
) -> dict:
    """Upload a bill/invoice: store it (SHA-256), parse it, and queue the extraction.
    parser=claude runs the OCR graph; parser=bayou submits to Bayou (poll to refresh)."""
    data = await file.read()
    evidence = _guard(
        store.upload_evidence, data, file_name=file.filename or "document",
        content_type=file.content_type, document_type=doc_kind,
        inventory_id=inventory_id, access_token=user.access_token, user_id=user.user_id,
    )
    if parser == "bayou":
        return _bayou_submit(
            data, file.filename or "bill.pdf", doc_kind, inventory_id, evidence["id"], user
        )

    session_id = uuid.uuid4().hex
    state = start_ocr(session_id, doc_kind, base64.b64encode(data).decode(), file.content_type)
    row = _guard(
        store.create_ocr_extraction,
        {
            "inventory_id": inventory_id,
            "evidence_document_id": evidence["id"],
            "graph_session_id": session_id,
            "doc_kind": doc_kind,
            "parser": "claude",
            "extracted": state.get("extraction") or {},
            "min_confidence": state.get("min_confidence"),
            "status": "pending_review" if state.get("needs_review") else "approved",
        },
        access_token=user.access_token, user_id=user.user_id,
    )
    return {**row, "needs_review": bool(state.get("needs_review"))}


def _bayou_submit(
    pdf_bytes, file_name, doc_kind, inventory_id, evidence_id, user: CurrentUser
) -> dict:
    client = BayouClient()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Bayou is not configured (set BAYOU_API_KEY).")
    try:
        bill_id = client.submit_bill(pdf_bytes, file_name)
    except BayouError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    row = _guard(
        store.create_ocr_extraction,
        {
            "inventory_id": inventory_id,
            "evidence_document_id": evidence_id,
            "graph_session_id": bill_id,      # no LangGraph run for Bayou
            "doc_kind": doc_kind,
            "parser": "bayou",
            "bayou_bill_id": bill_id,
            "extracted": {},
            "status": "parsing",
        },
        access_token=user.access_token, user_id=user.user_id,
    )
    return {**row, "needs_review": True}


@router.post("/ocr/{extraction_id}/refresh")
def ocr_refresh(extraction_id: str, user: CurrentUser = Depends(require_editor)) -> dict:
    """Poll Bayou for a parsing bill; when parsed, fill the extraction (Tier-2, approved)."""
    ext = _guard(store.get_ocr_extraction, extraction_id,
                 access_token=user.access_token, user_id=user.user_id)
    if ext is None:
        raise HTTPException(status_code=404, detail="Extraction not found.")
    if ext.get("parser") != "bayou" or not ext.get("bayou_bill_id"):
        raise HTTPException(status_code=400, detail="Refresh only applies to Bayou extractions.")

    client = BayouClient()
    if not client.is_configured:
        raise HTTPException(status_code=503, detail="Bayou is not configured (set BAYOU_API_KEY).")
    try:
        bill = client.get_bill(ext["bayou_bill_id"])
    except BayouError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if bill.status != "parsed":
        return ext                                     # still parsing
    extraction = bayou_bill_to_extraction(bill)
    return _guard(
        store.update_ocr_extraction, extraction_id,
        {
            "extracted": extraction.to_dict(),
            "min_confidence": extraction.min_confidence,
            "status": "approved",                      # trained parser -> trusted Tier 2
        },
        access_token=user.access_token, user_id=user.user_id,
    )


@router.get("/ocr/queue")
def ocr_queue(
    status: str = Query("pending_review"), user: CurrentUser = Depends(get_current_user)
) -> list[dict]:
    return _guard(store.list_ocr_queue, status=status,
                  access_token=user.access_token, user_id=user.user_id)


@router.post("/ocr/{extraction_id}/review")
def ocr_review(
    extraction_id: str, req: OcrReviewRequest, user: CurrentUser = Depends(require_editor)
) -> dict:
    """Approve (with corrections -> creates the emission record) or reject a queued extraction."""
    ext = _guard(store.get_ocr_extraction, extraction_id,
                 access_token=user.access_token, user_id=user.user_id)
    if ext is None:
        raise HTTPException(status_code=404, detail="Extraction not found.")

    # Resume the graph if it is paused at the human-review checkpoint.
    graph_state = get_ocr_state(ext["graph_session_id"])
    if graph_state and graph_state.get("phase") == "review":
        review_ocr(ext["graph_session_id"], req.action, req.corrected_fields)

    if req.action == "reject":
        return _guard(store.update_ocr_extraction, extraction_id, {"status": "rejected"},
                      access_token=user.access_token, user_id=user.user_id)

    required = (req.emission_source_id, req.fuel_or_activity, req.activity_value,
                req.activity_unit, req.period_start, req.period_end)
    if not all(required):
        raise HTTPException(
            status_code=422,
            detail="Approving requires emission_source_id, fuel_or_activity, "
                   "activity_value, activity_unit, period_start, period_end.",
        )
    is_bayou = ext.get("parser") == "bayou"
    record_req = StationaryRecordRequest(
        inventory_id=ext["inventory_id"],
        emission_source_id=req.emission_source_id,
        period_start=req.period_start,
        period_end=req.period_end,
        fuel_or_activity=req.fuel_or_activity,
        activity_value=req.activity_value,
        activity_unit=req.activity_unit,
        data_quality_tier=2 if is_bayou else req.data_quality_tier,   # Bayou = Tier 2
        activity_data_source="bayou" if is_bayou else "ocr",
        evidence_document_id=ext["evidence_document_id"],
    )
    try:
        record = _persist_stationary(record_req, user)
    except MissingEmissionFactor as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _guard(
        store.update_ocr_extraction, extraction_id,
        {"status": "applied", "applied_record_id": record["id"]},
        access_token=user.access_token, user_id=user.user_id,
    )


# --- Data-collection orchestration ------------------------------------------

@router.post("/inventories/{inventory_id}/collection/init")
def init_collection(inventory_id: str, user: CurrentUser = Depends(require_editor)) -> list[dict]:
    """Create 'missing' collection rows for every in-scope source in the inventory period."""
    inv = _guard(store.get_inventory, inventory_id,
                 access_token=user.access_token, user_id=user.user_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    sources = _guard(store.list_sources, access_token=user.access_token, user_id=user.user_id)
    existing = {
        s["emission_source_id"]
        for s in _guard(store.list_collection_status, inventory_id,
                        access_token=user.access_token, user_id=user.user_id)
    }
    created: list[dict] = []
    for src in sources:
        if src.get("is_excluded") or src["id"] in existing:
            continue
        created.append(
            _guard(
                store.upsert_collection_status,
                {
                    "inventory_id": inventory_id,
                    "emission_source_id": src["id"],
                    "period_start": inv["period_start"],
                    "period_end": inv["period_end"],
                    "status": "missing",
                },
                access_token=user.access_token,
                user_id=user.user_id,
            )
        )
    return created


@router.post("/collection/status")
def set_collection_status(
    req: CollectionStatusRequest, user: CurrentUser = Depends(require_editor)
) -> dict:
    return _guard(store.upsert_collection_status, req.model_dump(exclude_none=True),
                  access_token=user.access_token, user_id=user.user_id)


# --- Readiness meter --------------------------------------------------------

@router.get("/inventories/{inventory_id}/readiness", response_model=ReadinessResponse)
def readiness(
    inventory_id: str, user: CurrentUser = Depends(get_current_user)
) -> ReadinessResponse:
    statuses = _guard(store.list_collection_status, inventory_id,
                      access_token=user.access_token, user_id=user.user_id)
    total = len(statuses)
    complete = sum(1 for s in statuses if s.get("status") in _COMPLETE_STATUSES)
    by_status = Counter(s.get("status", "missing") for s in statuses)
    return ReadinessResponse(
        total=total,
        complete=complete,
        completeness_pct=(complete / total * 100.0) if total else 0.0,
        by_status=dict(by_status),
        items=statuses,
    )


# --- Onboarding wizard ------------------------------------------------------

@router.get("/onboarding", response_model=OnboardingResponse)
def onboarding(user: CurrentUser = Depends(get_current_user)) -> OnboardingResponse:
    """Backend-driven guided-setup checklist reflecting the org's real progress."""
    kw = {"access_token": user.access_token, "user_id": user.user_id}
    entities = _guard(store.list_entities, **kw)
    facilities = _guard(store.list_facilities, **kw)
    sources = _guard(store.list_sources, **kw)
    inventories = _guard(store.list_inventories, **kw)

    records = 0
    locked = 0
    for inv in inventories:
        if inv.get("locked"):
            locked += 1
        records += len(
            _guard(store.list_records_for_inventory, inv["id"], **kw)
        )

    checklist = build_onboarding(
        OnboardingCounts(
            entities=len(entities),
            facilities=len(facilities),
            sources=sum(1 for s in sources if not s.get("is_excluded")),
            inventories=len(inventories),
            records=records,
            locked_inventories=locked,
        )
    )
    return OnboardingResponse(
        steps=[OnboardingStepDTO(**vars(s)) for s in checklist.steps],
        complete=checklist.complete,
        total=checklist.total,
        pct=checklist.pct,
        next_key=checklist.next_key,
    )


# --- Reporting --------------------------------------------------------------

@router.get("/inventories/{inventory_id}/report", response_model=InventoryReportResponse)
def inventory_report(
    inventory_id: str,
    ar_version: str = Query("AR5"),
    user: CurrentUser = Depends(get_current_user),
) -> InventoryReportResponse:
    report = _assemble_report(inventory_id, ar_version, user)
    return InventoryReportResponse(
        ar_version=report.ar_version,
        total_scope1_tco2e=report.total_scope1_tco2e,
        biogenic_co2_tco2e=report.biogenic_co2_tco2e,
        by_gas=GasBreakdownDTO(
            co2_fossil_tco2e=report.by_gas.co2_fossil_tco2e,
            ch4_tco2e=report.by_gas.ch4_tco2e,
            n2o_tco2e=report.by_gas.n2o_tco2e,
            sf6_tco2e=report.by_gas.sf6_tco2e,
            nf3_tco2e=report.by_gas.nf3_tco2e,
            total_tco2e=report.by_gas.total_tco2e,
        ),
        by_facility=[
            FacilityBreakdownDTO(
                facility_id=f.facility_id, facility_name=f.facility_name, tco2e=f.tco2e
            )
            for f in report.by_facility
        ],
        record_count=report.record_count,
    )


@router.get("/inventories/{inventory_id}/report/xlsx")
def export_report_xlsx(
    inventory_id: str,
    ar_version: str = Query("AR5"),
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """Structured SB 253 / GHG Protocol disclosure workbook (coversheet + by gas + by facility)."""
    report = _assemble_report(inventory_id, ar_version, user)
    meta = _disclosure_meta(inventory_id, ar_version, user)
    data = build_xlsx(report, meta)
    filename = f"scope1-{meta.reporting_year}-{ar_version}.xlsx"
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/inventories/{inventory_id}/report/sb253.pdf")
def export_report_pdf(
    inventory_id: str,
    ar_version: str = Query("AR5"),
    user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    """Human-readable CA SB 253 / GHG Protocol Scope 1 disclosure PDF."""
    report = _assemble_report(inventory_id, ar_version, user)
    meta = _disclosure_meta(inventory_id, ar_version, user)
    data = build_pdf(report, meta)
    filename = f"scope1-sb253-{meta.reporting_year}-{ar_version}.pdf"
    return StreamingResponse(
        iter([data]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/records/{record_id}/trace")
def record_trace(
    record_id: str,
    ar_version: str = Query("AR5"),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """View Source: the activity x EF x GWP chain behind a record's number."""
    rec = _guard(store.get_record, record_id,
                 access_token=user.access_token, user_id=user.user_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Record not found.")
    sources = {s["id"]: s for s in _guard(
        store.list_sources, access_token=user.access_token, user_id=user.user_id)}
    facilities = {f["id"]: f["name"] for f in _guard(
        store.list_facilities, access_token=user.access_token, user_id=user.user_id)}
    boundaries = {b["entity_id"]: float(b["consolidation_multiplier"]) for b in _guard(
        store.list_boundaries, rec["inventory_id"],
        access_token=user.access_token, user_id=user.user_id)}

    report_record = _report_record(rec, sources, facilities, boundaries)
    trace = trace_record(report_record, ar_version)
    trace["ef_source"] = rec.get("ef_source")
    trace["ef_tier"] = rec.get("ef_tier")
    trace["evidence_document_id"] = rec.get("evidence_document_id")
    return trace


# --- Internal helpers -------------------------------------------------------

def _persist_stationary(req: StationaryRecordRequest, user: CurrentUser) -> dict:
    """Calculate + persist one stationary record (shared by single + CSV intake)."""
    result = calculate_stationary(
        req.fuel_or_activity, req.activity_value, req.activity_unit, _library(),
        biogenic=req.biogenic, hhv_override=req.hhv_override,
        data_quality_tier=req.data_quality_tier,
    )
    row = _record_row(req, result, req.activity_value, req.activity_unit)
    record = _guard(store.create_record, row,
                    access_token=user.access_token, user_id=user.user_id)
    _advance_collection(req, user)
    _log(record["id"], "create", user)
    return record


def _persist_mobile(req: MobileRecordRequest, user: CurrentUser) -> dict:
    """Calculate + persist one mobile record (shared by single + CSV intake)."""
    result = calculate_mobile(
        req.fuel_or_activity, req.fuel_quantity, req.fuel_unit, _library(),
        miles=req.miles, model_year=req.model_year,
        distance_activity=req.distance_activity, data_quality_tier=req.data_quality_tier,
    )
    row = _record_row(req, result, req.fuel_quantity, req.fuel_unit)
    record = _guard(store.create_record, row,
                    access_token=user.access_token, user_id=user.user_id)
    _advance_collection(req, user)
    _log(record["id"], "create", user)
    return record


def _persist_csv_row(row, source_id: str, inv: dict, user: CurrentUser) -> dict:
    """Build the matching record request from a parsed CSV row and persist it."""
    common = {
        "inventory_id": inv["id"],
        "emission_source_id": source_id,
        "period_start": inv["period_start"],
        "period_end": inv["period_end"],
        "data_quality_tier": row.tier,
        "activity_data_source": "csv",
    }
    if row.category == "stationary":
        return _persist_stationary(
            StationaryRecordRequest(
                fuel_or_activity=row.fuel, activity_value=row.amount,
                activity_unit=row.unit, biogenic=row.biogenic, **common,
            ),
            user,
        )
    return _persist_mobile(
        MobileRecordRequest(
            fuel_or_activity=row.fuel, fuel_quantity=row.amount, fuel_unit=row.unit,
            miles=row.miles, model_year=row.model_year,
            distance_activity="gasoline_passenger_car" if row.miles else None,
            **common,
        ),
        user,
    )


def _advance_collection(req, user: CurrentUser) -> None:
    """Auto-advance a source-period's collection status to 'entered' after a
    record is saved, so the readiness meter reflects data as it arrives."""
    store.upsert_collection_status(
        {
            "inventory_id": req.inventory_id,
            "emission_source_id": req.emission_source_id,
            "period_start": req.period_start,
            "period_end": req.period_end,
            "status": "entered",
        },
        access_token=user.access_token,
        user_id=user.user_id,
    )


def _log(
    entity_id: str,
    action: str,
    user: CurrentUser,
    *,
    entity_table: str = "s1_emission_record",
    field_changes: dict | None = None,
) -> None:
    """Append an immutable audit-trail entry (best-effort; never fails the write)."""
    store.log_change(
        entity_table, entity_id, action,
        field_changes=field_changes,
        access_token=user.access_token, user_id=user.user_id,
    )


def _record_row(req, result, activity_value: float, activity_unit: str) -> dict:
    gm = result.gas_masses
    co2_ref = next((r for r in result.ef_refs if r.gas == "CO2"), result.ef_refs[0])
    return {
        "inventory_id": req.inventory_id,
        "emission_source_id": req.emission_source_id,
        "period_start": req.period_start,
        "period_end": req.period_end,
        "activity_data_value": activity_value,
        "activity_data_unit": activity_unit,
        "activity_data_source": req.activity_data_source,
        "calculation_method": result.calculation_method,
        "heat_input_mmbtu": result.heat_input_mmbtu,
        "ef_source": f"{co2_ref.source} ({co2_ref.source_version})",
        "ef_tier": "T2" if result.calculation_method == "EF_Tier2" else "T1",
        "ef_selection_rank": co2_ref.selection_rank,
        "kg_co2_fossil": gm.kg_co2_fossil,
        "kg_co2_biogenic": gm.kg_co2_biogenic,
        "kg_ch4": gm.kg_ch4,
        "kg_n2o": gm.kg_n2o,
        "biogenic_fossil_tag": result.biogenic_fossil_tag,
        "data_quality_tier": result.data_quality_tier,
        "evidence_document_id": req.evidence_document_id,
    }


def _gas_masses(row: dict) -> GasMasses:
    return GasMasses(
        kg_co2_fossil=float(row.get("kg_co2_fossil") or 0.0),
        kg_co2_biogenic=float(row.get("kg_co2_biogenic") or 0.0),
        kg_ch4=float(row.get("kg_ch4") or 0.0),
        kg_n2o=float(row.get("kg_n2o") or 0.0),
        kg_sf6=float(row.get("kg_sf6") or 0.0),
        kg_nf3=float(row.get("kg_nf3") or 0.0),
    )


def _assemble_report(inventory_id: str, ar_version: str, user: CurrentUser):
    """Fetch records + sources + facilities + boundaries and roll up the report."""
    records = _guard(store.list_records_for_inventory, inventory_id,
                     access_token=user.access_token, user_id=user.user_id)
    sources = {s["id"]: s for s in _guard(
        store.list_sources, access_token=user.access_token, user_id=user.user_id)}
    facilities = {f["id"]: f["name"] for f in _guard(
        store.list_facilities, access_token=user.access_token, user_id=user.user_id)}
    boundaries = {b["entity_id"]: float(b["consolidation_multiplier"]) for b in _guard(
        store.list_boundaries, inventory_id,
        access_token=user.access_token, user_id=user.user_id)}
    report_records = [_report_record(rec, sources, facilities, boundaries) for rec in records]
    try:
        return build_inventory_report(report_records, ar_version)
    except KeyError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _disclosure_meta(inventory_id: str, ar_version: str, user: CurrentUser) -> DisclosureMeta:
    inv = _guard(store.get_inventory, inventory_id,
                 access_token=user.access_token, user_id=user.user_id)
    if inv is None:
        raise HTTPException(status_code=404, detail="Inventory not found.")
    entity = _guard(store.get_entity, inv["reporting_entity_id"],
                    access_token=user.access_token, user_id=user.user_id) or {}
    return DisclosureMeta(
        entity_name=entity.get("name", "-"),
        jurisdiction=entity.get("jurisdiction", "US"),
        reporting_year=inv["reporting_year"],
        period_start=inv["period_start"],
        period_end=inv["period_end"],
        consolidation_approach=inv["consolidation_approach"],
        gwp_version=ar_version,
        base_year=inv["base_year"],
    )


def _report_record(rec: dict, sources: dict, facilities: dict, boundaries: dict) -> ReportRecord:
    source = sources.get(rec["emission_source_id"], {})
    entity_id = source.get("entity_id")
    facility_id = source.get("facility_id")
    return ReportRecord(
        record_id=rec["id"],
        gas_masses=_gas_masses(rec),
        multiplier=boundaries.get(entity_id, 1.0),   # default 1.0 if no boundary set
        facility_id=facility_id,
        facility_name=facilities.get(facility_id),
        source_id=rec["emission_source_id"],
        source_name=source.get("source_name"),
    )
