"""Scope 2 ingestion routes — CSV bulk-import preview + commit (PRD 5.1).

`preview-csv` is stateless: parse + validate + normalize under a column mapping.
`import-csv` persists the result: it resolves each row's site_ref to an existing
site by name, finds-or-creates a csv account per (site, carrier), and inserts bill
rows. Rows whose site_ref matches no site are reported as unresolved, not saved.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.middleware.auth import CurrentUser, get_current_user
from api.models.scope2_schemas import (
    CsvBillPreviewDTO,
    CsvCommitResponse,
    CsvImportRequest,
    CsvPreviewResponse,
    CsvRowErrorDTO,
)
from api.routes.scope2_deps import resolve_org_id
from db import s2_bill_store, s2_site_store
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


@router.post("/bills/import-csv", response_model=CsvCommitResponse)
def commit_csv(
    request: CsvImportRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> CsvCommitResponse:
    """Persist a CSV import: resolve sites by name, create accounts, insert bills."""
    org_id = resolve_org_id(current_user)
    token = current_user.access_token
    try:
        result = import_bills_csv(request.csv_text, request.mapping)
    except ColumnMappingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    name_to_site_id = {
        (site["name"] or "").strip().lower(): site["site_id"]
        for site in s2_site_store.list_sites(token)
    }

    account_cache: dict[tuple[int, str], int] = {}
    rows: list[dict] = []
    unresolved: set[str] = set()

    for bill in result.bills:
        site_id = name_to_site_id.get(bill.site_ref.strip().lower())
        if site_id is None:
            unresolved.add(bill.site_ref)
            continue
        carrier = "electricity"
        key = (site_id, carrier)
        if key not in account_cache:
            account_cache[key] = s2_bill_store.get_or_create_account(
                site_id,
                carrier,
                org_id=org_id,
                user_id=current_user.user_id,
                access_token=token,
            )
        rows.append(
            {
                "account_id": account_cache[key],
                "period_start": bill.period_start.isoformat(),
                "period_end": bill.period_end.isoformat(),
                "raw_quantity": bill.raw_quantity,
                "raw_unit": bill.raw_unit,
                "canonical_mwh": bill.canonical_mwh,
                "cost_usd": bill.cost_usd,
                "is_estimated_read": bill.is_estimated_read,
                "is_cost_only": bill.is_cost_only,
                "conversion_note": bill.conversion_note,
                "ingestion_method": "csv",
            }
        )

    committed = s2_bill_store.insert_bills(
        rows, org_id=org_id, user_id=current_user.user_id, access_token=token
    )
    return CsvCommitResponse(
        total_rows=result.total_rows,
        committed_count=committed,
        error_count=len(result.errors),
        unresolved_site_refs=sorted(unresolved),
    )
