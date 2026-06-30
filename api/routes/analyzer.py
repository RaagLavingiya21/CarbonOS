"""FastAPI routes for BOM parsing, footprint calculation, and saved analyses."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    AnalysisDetailDTO,
    AnalysisSummaryDTO,
    AnalyzeResponse,
    CalculateFootprintRequest,
    CalculateFootprintResponse,
    CriticReportDTO,
    DeleteSessionResponse,
    EFMatchDTO,
    FootprintResultDTO,
    MatchFactorsRequest,
    MatchFactorsResponse,
    ParseBOMResponse,
    ParsedBOMDTO,
    SaveAnalysisRequest,
    SaveAnalysisResponse,
)
from api.services.session_store import WorkflowSession, session_store
from calc.critic import run_critic
from calc.footprint import calculate_footprint
from db.reader import get_product_by_id, get_products_for_active_org
from db.store import save_analysis
from factors.ef_lookup import EFMatch, lookup_ef
from parsing.bom_parser import ParsedBOM, parse_bom_csv

router = APIRouter(tags=["analyzer"])


def _product_name_from_upload(upload: UploadFile) -> str:
    filename = upload.filename or "Unknown Product"
    return filename.removesuffix(".csv").replace("_", " ").title()


def _session_or_404(session_id: str) -> WorkflowSession:
    session = session_store.get(session_id, workflow="analyzer")
    if session is None:
        raise HTTPException(status_code=404, detail=f"Analyzer session '{session_id}' not found.")
    return session


def _match_factors_for_bom(bom: ParsedBOM) -> tuple[list[EFMatch | None], list[str]]:
    ef_matches: list[EFMatch | None] = []
    warnings: list[str] = []
    for row in bom.rows:
        if not row.material:
            ef_matches.append(None)
            continue

        ef = lookup_ef(row.material, row.country_of_origin)
        ef_matches.append(ef)
        if ef.is_no_match:
            warnings.append(
                f"Row {row.row_index + 1} ({row.material!r}): no emission factor match. "
                f"Suggestions: {', '.join(ef.suggested_alternatives) or 'none'}."
            )
        elif ef.is_low_confidence:
            warnings.append(
                f"Row {row.row_index + 1} ({row.material!r}): low-confidence match to "
                f"'{ef.sector_name}' ({ef.confidence_score:.0f}%). "
                f"Suggestions: {', '.join(ef.suggested_alternatives) or 'none'}."
            )
    return ef_matches, warnings


def _result_csv_rows(detail: dict) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in detail.get("line_items", []):
        rows.append(
            {
                "Component": item.get("component") or "",
                "Material": item.get("material") or "",
                "Spend (USD)": item.get("spend_usd"),
                "Matched Sector": item.get("matched_sector") or "",
                "EF (kg CO2e/USD)": item.get("emission_factor"),
                "EF Source": item.get("ef_source") or "",
                "kg CO2e": item.get("kg_co2e"),
                "Share (%)": item.get("share_pct"),
                "Status": item.get("flag_status") or "",
            }
        )
    return rows


@router.post("/api/analyze/parse", response_model=ParseBOMResponse)
async def parse_bom(
    file: UploadFile = File(...),
    product_name: str | None = Form(None),
) -> ParseBOMResponse:
    raw_bytes = await file.read()
    bom = parse_bom_csv(raw_bytes, product_name or _product_name_from_upload(file))
    session = session_store.create("analyzer", "bom_review", bom=bom, file_key=file.filename)
    return ParseBOMResponse(
        session_id=session.session_id,
        phase="bom_review",
        bom=ParsedBOMDTO.from_domain(bom),
    )


@router.post("/api/analyze/match-factors", response_model=MatchFactorsResponse)
def match_factors(request: MatchFactorsRequest) -> MatchFactorsResponse:
    session = _session_or_404(request.session_id)
    bom: ParsedBOM | None = session.data.get("bom")
    if bom is None:
        raise HTTPException(status_code=409, detail="No parsed BOM found for this session.")

    ef_matches, warnings = _match_factors_for_bom(bom)
    session_store.update(
        session.session_id,
        phase="ef_review",
        ef_matches=ef_matches,
        ef_warnings=warnings,
    )
    return MatchFactorsResponse(
        session_id=session.session_id,
        phase="ef_review",
        ef_matches=[EFMatchDTO.from_domain(match) for match in ef_matches],
        warnings=warnings,
    )


@router.post("/api/analyze/calculate", response_model=CalculateFootprintResponse)
def calculate(request: CalculateFootprintRequest) -> CalculateFootprintResponse:
    session = _session_or_404(request.session_id)
    bom: ParsedBOM | None = session.data.get("bom")
    ef_matches: list[EFMatch | None] | None = session.data.get("ef_matches")
    if bom is None:
        raise HTTPException(status_code=409, detail="No parsed BOM found for this session.")
    if ef_matches is None:
        raise HTTPException(status_code=409, detail="No emission factor matches found.")

    result = calculate_footprint(bom, ef_matches)
    result, critic_report = run_critic(result)
    session_store.update(
        session.session_id,
        phase="calc_review",
        result=result,
        critic_report=critic_report,
    )
    return CalculateFootprintResponse(
        session_id=session.session_id,
        phase="calc_review",
        result=FootprintResultDTO.from_domain(result),
        critic_report=CriticReportDTO.from_domain(critic_report),
    )


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    product_name: str | None = Form(None),
    save: bool = Form(False),
    status: Literal["approved", "flagged"] = Form("approved"),
    flagged_comment: str | None = Form(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> AnalyzeResponse:
    raw_bytes = await file.read()
    bom = parse_bom_csv(raw_bytes, product_name or _product_name_from_upload(file))
    session = session_store.create("analyzer", "bom_review", bom=bom, file_key=file.filename)

    ef_matches, warnings = _match_factors_for_bom(bom)
    result = calculate_footprint(bom, ef_matches)
    result, critic_report = run_critic(result)
    product_id = None
    phase: Literal["calc_review", "saved"] = "calc_review"

    if save:
        if status == "flagged" and not (flagged_comment or "").strip():
            raise HTTPException(
                status_code=422,
                detail="flagged_comment is required when status is 'flagged'.",
            )
        product_id = save_analysis(
            product_name or bom.product_name,
            result,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
            analysis_date=date.today(),
            status=status,
            flagged_comment=flagged_comment,
        )
        phase = "saved"

    session_store.update(
        session.session_id,
        phase=phase,
        ef_matches=ef_matches,
        ef_warnings=warnings,
        result=result,
        critic_report=critic_report,
        saved_product_id=product_id,
    )
    return AnalyzeResponse(
        session_id=session.session_id,
        phase=phase,
        bom=ParsedBOMDTO.from_domain(bom),
        ef_matches=[EFMatchDTO.from_domain(match) for match in ef_matches],
        warnings=warnings,
        result=FootprintResultDTO.from_domain(result),
        critic_report=CriticReportDTO.from_domain(critic_report),
        product_id=product_id,
    )


@router.post("/api/analyses", response_model=SaveAnalysisResponse)
def save_analysis_result(
    request: SaveAnalysisRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> SaveAnalysisResponse:
    session = _session_or_404(request.session_id)
    result = session.data.get("result")
    if result is None:
        raise HTTPException(status_code=409, detail="No calculated footprint result found.")
    if request.status == "flagged" and not (request.flagged_comment or "").strip():
        raise HTTPException(
            status_code=422,
            detail="flagged_comment is required when status is 'flagged'.",
        )

    product_id = save_analysis(
        request.product_name,
        result,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
        analysis_date=date.today(),
        status=request.status,
        flagged_comment=request.flagged_comment,
    )
    session_store.update(session.session_id, phase="saved", saved_product_id=product_id)
    return SaveAnalysisResponse(product_id=product_id, phase="saved")


@router.get("/api/analyses", response_model=list[AnalysisSummaryDTO])
def list_analyses(
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AnalysisSummaryDTO]:
    return [
        AnalysisSummaryDTO.from_row(row)
        for row in get_products_for_active_org(
            current_user.access_token,
            user_id=current_user.user_id,
        )
    ]


@router.get("/api/analyses/{product_id}", response_model=AnalysisDetailDTO)
def get_analysis(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> AnalysisDetailDTO:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    return AnalysisDetailDTO.from_row(product)


@router.get("/api/analyses/{product_id}/export")
def export_analysis(
    product_id: int,
    format: Literal["csv"] = "csv",
    current_user: CurrentUser = Depends(get_current_user),
) -> StreamingResponse:
    if format != "csv":
        raise HTTPException(status_code=422, detail="Only CSV export is supported.")
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")

    rows = _result_csv_rows(product)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()) if rows else [])
    if rows:
        writer.writeheader()
        writer.writerows(rows)
    filename = f"{product['product_name'].replace(' ', '_')}_footprint.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/api/analyze/sessions/{session_id}", response_model=DeleteSessionResponse)
def delete_analyzer_session(session_id: str) -> DeleteSessionResponse:
    return DeleteSessionResponse(deleted=session_store.delete(session_id))
