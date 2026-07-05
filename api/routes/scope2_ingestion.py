"""Scope 2 ingestion routes — CSV bulk-import preview (PRD 5.1).

M0 exposes a stateless preview: parse + validate + normalize a utility-bill CSV
under a column mapping and return the parsed bills and per-row errors. Persisting
bills (account linkage, dedup/true-up) lands with the ingestion write path in M1.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    CsvBillPreviewDTO,
    CsvImportRequest,
    CsvPreviewResponse,
    CsvRowErrorDTO,
)
from s2_ingestion.csv_import import ColumnMappingError, import_bills_csv

router = APIRouter(prefix="/api/scope2", tags=["scope2"])


@router.post("/bills/preview-csv", response_model=CsvPreviewResponse)
def preview_csv(
    request: CsvImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CsvPreviewResponse:
    try:
        result = import_bills_csv(request.csv_text, request.mapping)
    except ColumnMappingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    bills = [
        CsvBillPreviewDTO(
            site_ref=b.site_ref,
            period_start=b.period_start.isoformat(),
            period_end=b.period_end.isoformat(),
            canonical_mwh=b.canonical_mwh,
            cost_usd=b.cost_usd,
            is_cost_only=b.is_cost_only,
            is_estimated_read=b.is_estimated_read,
            conversion_note=b.conversion_note,
        )
        for b in result.bills
    ]
    errors = [
        CsvRowErrorDTO(row_index=e.row_index, message=e.message) for e in result.errors
    ]
    return CsvPreviewResponse(
        total_rows=result.total_rows,
        valid_count=len(bills),
        error_count=len(errors),
        bills=bills,
        errors=errors,
    )
