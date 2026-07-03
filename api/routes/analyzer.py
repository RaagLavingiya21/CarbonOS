"""FastAPI routes for BOM parsing, footprint calculation, and saved analyses."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse, StreamingResponse

from api.middleware.auth import CurrentUser, get_current_user
from api.models.schemas import (
    AnalysisDetailDTO,
    AnalysisSummaryDTO,
    AnalyzeResponse,
    ApplyPrimaryDataRequest,
    ApplyPrimaryDataResponse,
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
    PublishAnalysisResponse,
    SaveAnalysisRequest,
    SaveAnalysisResponse,
)
from api.services.session_store import WorkflowSession, session_store
from calc.critic import run_critic
from calc.footprint import calculate_footprint
from db.org_store import get_active_org
from db.reader import get_footprint_provenance, get_product_by_id, get_products_for_active_org
from db.store import apply_primary_data, publish_analysis, save_analysis
from exchange.pact import build_product_footprint, validate_product_footprint
from exchange.provenance import build_provenance_markdown
from factors.ef_lookup import EFMatch, lookup_ef
from parsing.bom_parser import ParsedBOM, parse_bom_csv

router = APIRouter(tags=["analyzer"])


def _parse_optional_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    return date.fromisoformat(value.strip())


def _default_reporting_period(analysis_date: date) -> tuple[date, date]:
    return date(analysis_date.year, 1, 1), date(analysis_date.year, 12, 31)


def _normalize_geography_country(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    normalized = value.strip().upper()
    if len(normalized) != 2 or not normalized.isalpha():
        raise HTTPException(
            status_code=422,
            detail="geography_country must be a two-letter ISO 3166-1 alpha-2 code",
        )
    return normalized


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
    product_description: str | None = Form(None),
    reporting_period_start: str | None = Form(None),
    reporting_period_end: str | None = Form(None),
    geography_country: str | None = Form(None),
    recalculate_of_product_id: int | None = Form(None),
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
    analysis_date = date.today()
    period_start = _parse_optional_date(reporting_period_start)
    period_end = _parse_optional_date(reporting_period_end)
    if period_start is None or period_end is None:
        period_start, period_end = _default_reporting_period(analysis_date)

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
            analysis_date=analysis_date,
            status=status,
            flagged_comment=flagged_comment,
            product_description=product_description,
            reporting_period_start=period_start,
            reporting_period_end=period_end,
            geography_country=_normalize_geography_country(geography_country),
            recalculate_of_product_id=recalculate_of_product_id,
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

    analysis_date = date.today()
    period_start = request.reporting_period_start
    period_end = request.reporting_period_end
    if period_start is None or period_end is None:
        period_start, period_end = _default_reporting_period(analysis_date)

    product_id = save_analysis(
        request.product_name,
        result,
        user_id=current_user.user_id,
        access_token=current_user.access_token,
        analysis_date=analysis_date,
        status=request.status,
        flagged_comment=request.flagged_comment,
        product_description=request.product_description,
        reporting_period_start=period_start,
        reporting_period_end=period_end,
        geography_country=request.geography_country,
        recalculate_of_product_id=request.recalculate_of_product_id,
    )
    session_store.update(session.session_id, phase="saved", saved_product_id=product_id)
    return SaveAnalysisResponse(product_id=product_id, phase="saved")


@router.get("/api/analyses", response_model=list[AnalysisSummaryDTO])
def list_analyses(
    status: str | None = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
) -> list[AnalysisSummaryDTO]:
    return [
        AnalysisSummaryDTO.from_row(row)
        for row in get_products_for_active_org(
            current_user.access_token,
            user_id=current_user.user_id,
            status=status,
        )
    ]


@router.get("/api/analyses/summary")
def get_portfolio_summary(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    products = get_products_for_active_org(
        current_user.access_token,
        user_id=current_user.user_id,
    )
    total_kg_co2e = sum(p.get("total_kg_co2e") or 0 for p in products)
    pds_values = [p.get("primary_data_share") or 0 for p in products]
    avg_primary_data_share = sum(pds_values) / len(pds_values) if pds_values else 0.0
    counts_by_status: dict[str, int] = {}
    for product in products:
        product_status = product.get("status") or "unknown"
        counts_by_status[product_status] = counts_by_status.get(product_status, 0) + 1
    open_flags_count = sum(1 for p in products if (p.get("flagged_items") or 0) > 0)
    return {
        "total_kg_co2e": total_kg_co2e,
        "avg_primary_data_share": avg_primary_data_share,
        "counts_by_status": counts_by_status,
        "open_flags_count": open_flags_count,
        "product_count": len(products),
    }


@router.get("/api/analyses/{product_id}", response_model=AnalysisDetailDTO)
def get_analysis(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> AnalysisDetailDTO:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    return AnalysisDetailDTO.from_row(product)


@router.post("/api/analyses/{product_id}/publish", response_model=PublishAnalysisResponse)
def publish_analysis_route(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> PublishAnalysisResponse:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    try:
        publish_analysis(
            product_id,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    updated = get_product_by_id(product_id, current_user.access_token)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    return PublishAnalysisResponse(
        product_id=product_id,
        status=updated["status"],
        published_at=updated["published_at"],
    )


@router.post(
    "/api/analyses/{product_id}/primary-data",
    response_model=ApplyPrimaryDataResponse,
)
def apply_primary_data_route(
    product_id: int,
    request: ApplyPrimaryDataRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> ApplyPrimaryDataResponse:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    try:
        result = apply_primary_data(
            product_id,
            request.item_id,
            request.primary_kg_co2e,
            request.source_note,
            user_id=current_user.user_id,
            access_token=current_user.access_token,
            engagement_id=request.engagement_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApplyPrimaryDataResponse(**result)


@router.get("/api/footprints/{product_id}/pact")
def export_pact(
    product_id: int,
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    product = get_product_by_id(product_id, current_user.access_token)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    if product.get("status") != "approved":
        raise HTTPException(
            status_code=409,
            detail="Only approved footprints can be exported.",
        )

    active_org = get_active_org(current_user.access_token, user_id=current_user.user_id)
    org_name = active_org.name if active_org else None
    org_id = active_org.id if active_org else None

    payload = build_product_footprint(product, org_name, org_id)
    violations = validate_product_footprint(payload)
    if violations:
        raise HTTPException(status_code=500, detail=violations)
    return payload


@router.get("/api/footprints/{product_id}/provenance")
def get_provenance(
    product_id: int,
    format: Literal["json", "markdown"] = Query("json"),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict | PlainTextResponse:
    provenance = get_footprint_provenance(product_id, current_user.access_token)
    if provenance is None:
        raise HTTPException(status_code=404, detail=f"Analysis {product_id} not found.")
    if format == "markdown":
        return PlainTextResponse(
            build_provenance_markdown(provenance),
            media_type="text/markdown; charset=utf-8",
        )
    return provenance


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
