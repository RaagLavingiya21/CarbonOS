"""Scope-3 questionnaire routes (Epic B). Orchestrate only — detection lives in
s3_questionnaire.framework_detector, mapping in s3_questionnaire.question_mapper,
inventory datapoints in db.s3_inventory_store, persistence in
db.s3_questionnaire_store. org_id resolved here.

Base path `/scope-3`. Ships dark. Written but NOT yet run against a live DB.
Note: `detect` reads the upload as UTF-8 text (works for .txt/.csv); structured
PDF/xlsx extraction is a deferred follow-up.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

import db.s3_inventory_store as inv_store
import db.s3_questionnaire_store as store
from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope3_schemas import (
    DetectResponse,
    MapResponse,
    QuestionDTO,
    QuestionMappingDTO,
    QuestionnaireCreateRequest,
    QuestionnaireDetailDTO,
    QuestionnaireRequestDTO,
)
from db.org_store import get_active_org
from s3_questionnaire.framework_detector import parse_questionnaire
from s3_questionnaire.models import ParsedQuestion
from s3_questionnaire.question_mapper import map_question

router = APIRouter(tags=["scope3-questionnaire"])


def _org_id(current_user: CurrentUser) -> str:
    org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    if org is None:
        raise HTTPException(status_code=400, detail="No active organization for this user.")
    return org.id


def _require_request(current_user: CurrentUser, request_id: int) -> dict:
    req = store.get_request(access_token=current_user.access_token, request_id=request_id)
    if req is None:
        raise HTTPException(status_code=404, detail=f"Questionnaire {request_id} not found.")
    return req


@router.post("/scope-3/questionnaires", response_model=QuestionnaireRequestDTO)
def create_questionnaire(
    body: QuestionnaireCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> QuestionnaireRequestDTO:
    fields = {
        "customer_name": body.customer_name,
        "framework": body.framework or "generic",
        "deadline": body.deadline,
        "inventory_id": body.inventory_id,
    }
    row = store.create_request(
        access_token=current_user.access_token,
        org_id=_org_id(current_user),
        user_id=current_user.user_id,
        fields=fields,
    )
    return QuestionnaireRequestDTO(**row)


@router.get("/scope-3/questionnaires", response_model=list[QuestionnaireRequestDTO])
def list_questionnaires(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[QuestionnaireRequestDTO]:
    rows = store.list_requests(access_token=current_user.access_token, org_id=_org_id(current_user))
    return [QuestionnaireRequestDTO(**r) for r in rows]


@router.post("/scope-3/questionnaires/{request_id}/detect", response_model=DetectResponse)
async def detect(
    request_id: int,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
) -> DetectResponse:
    req = _require_request(current_user, request_id)
    text = (await file.read()).decode("utf-8", errors="ignore")
    parsed = parse_questionnaire(text)

    store.update_request(
        access_token=current_user.access_token,
        request_id=request_id,
        patch={"framework": parsed.detected.framework, "status": "in_progress"},
    )
    store.replace_questions(
        access_token=current_user.access_token,
        org_id=req["org_id"],
        request_id=request_id,
        questions=[
            {
                "question_index": q.index,
                "question_text": q.text,
                "question_type": q.question_type,
                "framework_field_key": q.framework_field_key,
            }
            for q in parsed.questions
        ],
    )
    return DetectResponse(
        request_id=request_id,
        framework=parsed.detected.framework,
        is_low_confidence=parsed.detected.is_low_confidence,
        question_count=len(parsed.questions),
    )


@router.post("/scope-3/questionnaires/{request_id}/map", response_model=MapResponse)
def map_answers(
    request_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> MapResponse:
    req = _require_request(current_user, request_id)
    if not req.get("inventory_id"):
        raise HTTPException(
            status_code=400, detail="Attach an inventory_id to this questionnaire before mapping."
        )
    inventory = _build_inventory(current_user, req["inventory_id"])
    questions = store.list_questions(access_token=current_user.access_token, request_id=request_id)

    mapping_rows = []
    for q in questions:
        pq = ParsedQuestion(
            index=q["question_index"],
            text=q["question_text"],
            question_type=q["question_type"],
            framework_field_key=q.get("framework_field_key"),
        )
        m = map_question(pq, inventory)
        mapping_rows.append(
            {
                "question_id": q["question_id"],
                "datapoint_ref": m.datapoint_ref,
                "mapped_value": m.mapped_value,
                "answer_text": m.answer_text,
                "confidence_score": m.confidence_score,
                "method": m.method,
                "citation": m.citation,
                "flag_status": m.flag_status,
            }
        )
    store.replace_mappings(
        access_token=current_user.access_token,
        org_id=req["org_id"],
        question_ids=[q["question_id"] for q in questions],
        mappings=mapping_rows,
    )
    needs_human = sum(1 for m in mapping_rows if m["flag_status"] == "needs_human")
    return MapResponse(
        request_id=request_id,
        mapped=len(mapping_rows) - needs_human,
        needs_human=needs_human,
    )


@router.get("/scope-3/questionnaires/{request_id}", response_model=QuestionnaireDetailDTO)
def get_questionnaire(
    request_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> QuestionnaireDetailDTO:
    req = _require_request(current_user, request_id)
    questions = store.list_questions(access_token=current_user.access_token, request_id=request_id)
    mappings = store.list_mappings(
        access_token=current_user.access_token,
        question_ids=[q["question_id"] for q in questions],
    )
    return QuestionnaireDetailDTO(
        request=QuestionnaireRequestDTO(**req),
        questions=[
            QuestionDTO(
                question_id=q["question_id"],
                question_index=q["question_index"],
                question_text=q["question_text"],
                question_type=q["question_type"],
                framework_field_key=q.get("framework_field_key"),
            )
            for q in questions
        ],
        mappings=[
            QuestionMappingDTO(
                question_id=m["question_id"],
                datapoint_ref=m.get("datapoint_ref"),
                mapped_value=m.get("mapped_value"),
                answer_text=m.get("answer_text"),
                confidence_score=m.get("confidence_score") or 0.0,
                method=m["method"],
                citation=m.get("citation"),
                flag_status=m["flag_status"],
            )
            for m in mappings
        ],
    )


@router.post("/scope-3/questionnaires/{request_id}/submit", response_model=QuestionnaireRequestDTO)
def submit_questionnaire(
    request_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> QuestionnaireRequestDTO:
    req = _require_request(current_user, request_id)
    questions = {
        q["question_id"]: q
        for q in store.list_questions(access_token=current_user.access_token, request_id=request_id)
    }
    mappings = store.list_mappings(
        access_token=current_user.access_token, question_ids=list(questions)
    )
    entries = [
        {
            "framework_field_key": questions[m["question_id"]].get("framework_field_key"),
            "question_signature": questions[m["question_id"]]["question_text"][:200],
            "answer_text": m["answer_text"],
            "source_request_id": request_id,
        }
        for m in mappings
        if m.get("answer_text") and m["flag_status"] != "needs_human"
    ]
    store.add_library_entries(
        access_token=current_user.access_token,
        org_id=req["org_id"],
        user_id=current_user.user_id,
        entries=entries,
    )
    updated = store.update_request(
        access_token=current_user.access_token,
        request_id=request_id,
        patch={"status": "submitted"},
    )
    return QuestionnaireRequestDTO(**(updated or req))


# --- helpers ----------------------------------------------------------------


def _build_inventory(current_user: CurrentUser, inventory_id: int) -> dict:
    version = inv_store.get_inventory_version(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    if version is None:
        raise HTTPException(status_code=404, detail=f"Inventory {inventory_id} not found.")
    categories = inv_store.list_category_results(
        access_token=current_user.access_token, inventory_id=inventory_id
    )
    return {
        "total": version.get("total_kg_co2e"),
        "categories": {
            int(c["scope3_category"]): float(c["total_kg_co2e"] or 0) for c in categories
        },
    }
