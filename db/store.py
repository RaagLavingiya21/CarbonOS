"""Supabase persistence for product footprint analyses.

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from calc.dqr import aggregate_dqr, line_item_dqr
from calc.footprint import FootprintResult, LineItem
from calc.pds import compute_primary_data_share
from db.client import get_user_client
from db.copilot_store import append_audit_log, update_engagement
from db.reader import get_product_by_id
from factors.ef_lookup import lookup_ef_by_sector_code


@dataclass
class AnalysisSummary:
    product_id: int
    product_name: str
    analysis_date: str
    total_kg_co2e: float
    matched_items: int
    flagged_items: int


def init_db() -> None:
    """No-op: schema is managed by supabase/migrations/."""


def save_analysis(
    product_name: str,
    result: FootprintResult,
    *,
    user_id: str,
    access_token: str,
    analysis_date: date | None = None,
    status: str = "approved",
    flagged_comment: str | None = None,
    product_description: str | None = None,
    reporting_period_start: date | None = None,
    reporting_period_end: date | None = None,
    geography_country: str | None = None,
    recalculate_of_product_id: int | None = None,
) -> int:
    """Persist a footprint result. Returns the new product_id."""
    if analysis_date is None:
        analysis_date = date.today()

    if reporting_period_start is None or reporting_period_end is None:
        reporting_period_start = date(analysis_date.year, 1, 1)
        reporting_period_end = date(analysis_date.year, 12, 31)

    insert_data: dict = {
        "user_id": user_id,
        "product_name": product_name.strip(),
        "analysis_date": analysis_date.isoformat(),
        "total_kg_co2e": round(result.total_kg_co2e, 6),
        "matched_items": result.matched_count,
        "flagged_items": result.flagged_count,
        "status": status,
        "flagged_comment": flagged_comment.strip() if flagged_comment else None,
        "product_description": product_description.strip() if product_description else None,
        "reporting_period_start": reporting_period_start.isoformat(),
        "reporting_period_end": reporting_period_end.isoformat(),
        "geography_country": geography_country,
        "version": 1,
    }

    if recalculate_of_product_id is not None:
        source = get_product_by_id(recalculate_of_product_id, access_token)
        if source is None:
            raise ValueError(f"Source product {recalculate_of_product_id} not found.")
        insert_data["product_lineage_id"] = source["product_lineage_id"]
        insert_data["version"] = source["version"] + 1

    pds_rows = [
        {
            "kg_co2e": round(li.kg_co2e, 6) if li.is_matched else None,
            "data_source": "secondary",
        }
        for li in result.line_items
    ]
    insert_data["primary_data_share"] = compute_primary_data_share(pds_rows)

    reporting_year = _reporting_year(reporting_period_start)
    line_item_rows = [
        _line_item_row(product_id=0, user_id=user_id, li=li, reporting_year=reporting_year)
        for li in result.line_items
    ]
    aggregate = aggregate_dqr(line_item_rows)
    insert_data["technological_dqr"] = aggregate["technological"]
    insert_data["geographical_dqr"] = aggregate["geographical"]
    insert_data["temporal_dqr"] = aggregate["temporal"]
    insert_data["dqr_computed_at"] = datetime.now(UTC).isoformat()

    client = get_user_client(access_token)
    product_response = (
        client.table("products")
        .insert(insert_data)
        .execute()
    )
    product_id = product_response.data[0]["product_id"]

    for row in line_item_rows:
        row["product_id"] = product_id
    if line_item_rows:
        client.table("line_items").insert(line_item_rows).execute()

    return int(product_id)


def _reporting_year(reporting_period_start: date | str | None) -> int:
    if reporting_period_start is None:
        return date.today().year
    if isinstance(reporting_period_start, date):
        return reporting_period_start.year
    return date.fromisoformat(str(reporting_period_start)[:10]).year


def _dqr_fields_for_dict_row(
    row: dict,
    *,
    reporting_year: int,
) -> dict[str, int | float | str | None]:
    is_low = "low_confidence" in (row.get("flag_status") or "")
    dqr = line_item_dqr(
        ef_confidence=row.get("ef_confidence"),
        is_low_confidence=is_low,
        data_source=row.get("data_source") or "secondary",
        country_of_origin=row.get("country_of_origin"),
        reporting_year=reporting_year,
    )
    return {
        "ef_confidence": row.get("ef_confidence"),
        "country_of_origin": row.get("country_of_origin"),
        "technological_dqr": dqr["technological"],
        "geographical_dqr": dqr["geographical"],
        "temporal_dqr": dqr["temporal"],
    }


def publish_analysis(
    product_id: int,
    *,
    user_id: str,
    access_token: str,
) -> None:
    """Direct publish is disabled — footprints reach published only via approve_review."""
    raise ValueError(
        "Direct publish is not permitted. Submit for review and have a different "
        "org member approve the footprint."
    )


def submit_for_review(
    product_id: int,
    *,
    user_id: str,
    access_token: str,
) -> None:
    """Move an approved footprint to under_review."""
    product = get_product_by_id(product_id, access_token)
    if product is None:
        raise ValueError(f"Product {product_id} not found.")
    if product.get("status") != "approved":
        raise ValueError("Only approved footprints can be submitted for review.")

    submitted_at = datetime.now(UTC).isoformat()
    client = get_user_client(access_token)
    client.table("products").update(
        {
            "status": "under_review",
            "submitted_for_review_by": user_id,
            "submitted_at": submitted_at,
            "reviewed_by": None,
            "reviewed_at": None,
            "review_comment": None,
        }
    ).eq("product_id", product_id).execute()

    append_audit_log(
        event="submitted_for_review",
        workflow="footprint_lifecycle",
        user_id=user_id,
        access_token=access_token,
        product_name=product.get("product_name"),
        status="under_review",
    )


def approve_review(
    product_id: int,
    *,
    reviewer_user_id: str,
    access_token: str,
) -> None:
    """Publish a footprint after review by a different org member."""
    product = get_product_by_id(product_id, access_token)
    if product is None:
        raise ValueError(f"Product {product_id} not found.")
    if product.get("status") != "under_review":
        raise ValueError("Only footprints under review can be approved.")
    submitter = product.get("submitted_for_review_by")
    if submitter is not None and reviewer_user_id == submitter:
        raise ValueError("review requires a different approver")

    from db.org_store import get_active_org_member_ids

    member_ids = get_active_org_member_ids(access_token, user_id=reviewer_user_id)
    if member_ids and reviewer_user_id not in member_ids:
        raise ValueError("Reviewer must be a member of the active organization.")

    reviewed_at = datetime.now(UTC).isoformat()
    published_at = reviewed_at
    client = get_user_client(access_token)
    client.table("products").update(
        {
            "status": "published",
            "reviewed_by": reviewer_user_id,
            "reviewed_at": reviewed_at,
            "published_at": published_at,
        }
    ).eq("product_id", product_id).execute()

    append_audit_log(
        event="published",
        workflow="footprint_lifecycle",
        user_id=reviewer_user_id,
        access_token=access_token,
        product_name=product.get("product_name"),
        status="published",
    )


def reject_review(
    product_id: int,
    comment: str,
    *,
    reviewer_user_id: str,
    access_token: str,
) -> None:
    """Reject a footprint under review, returning it to flagged status."""
    product = get_product_by_id(product_id, access_token)
    if product is None:
        raise ValueError(f"Product {product_id} not found.")
    if product.get("status") != "under_review":
        raise ValueError("Only footprints under review can be rejected.")
    submitter = product.get("submitted_for_review_by")
    if submitter is not None and reviewer_user_id == submitter:
        raise ValueError("review requires a different approver")

    reviewed_at = datetime.now(UTC).isoformat()
    client = get_user_client(access_token)
    client.table("products").update(
        {
            "status": "flagged",
            "reviewed_by": reviewer_user_id,
            "reviewed_at": reviewed_at,
            "review_comment": comment.strip(),
        }
    ).eq("product_id", product_id).execute()

    append_audit_log(
        event="review_rejected",
        workflow="footprint_lifecycle",
        user_id=reviewer_user_id,
        access_token=access_token,
        product_name=product.get("product_name"),
        status="flagged",
    )


def apply_primary_data(
    source_product_id: int,
    item_id: int,
    primary_kg_co2e: float,
    source_note: str,
    *,
    user_id: str,
    access_token: str,
    engagement_id: int | None = None,
) -> dict:
    """Apply supplier primary data to a line item, creating a new footprint version."""
    source = get_product_by_id(source_product_id, access_token)
    if source is None:
        raise ValueError(f"Source product {source_product_id} not found.")

    source_items = source.get("line_items") or []
    matched = next((li for li in source_items if li.get("item_id") == item_id), None)
    if matched is None:
        raise ValueError(f"Line item {item_id} not found on product {source_product_id}.")

    pds_before = compute_primary_data_share(source_items)

    cloned_items: list[dict] = []
    for li in source_items:
        row = dict(li)
        if row.get("item_id") == item_id:
            row["kg_co2e"] = round(primary_kg_co2e, 6)
            row["data_source"] = "primary"
            row["ef_source"] = f"Supplier primary data: {source_note}"
            row["emission_factor"] = None
        cloned_items.append(row)

    total_kg_co2e = sum(li["kg_co2e"] for li in cloned_items if li.get("kg_co2e") is not None)
    for li in cloned_items:
        kg = li.get("kg_co2e")
        if kg is not None and total_kg_co2e > 0:
            li["share_pct"] = round(kg / total_kg_co2e * 100, 4)
        else:
            li["share_pct"] = None

    pds_after = compute_primary_data_share(cloned_items)
    new_version = int(source.get("version") or 1) + 1

    insert_data: dict = {
        "user_id": user_id,
        "product_name": source["product_name"],
        "analysis_date": source["analysis_date"],
        "total_kg_co2e": round(total_kg_co2e, 6),
        "matched_items": source.get("matched_items"),
        "flagged_items": source.get("flagged_items"),
        "status": "approved",
        "flagged_comment": source.get("flagged_comment"),
        "product_description": source.get("product_description"),
        "declared_unit": source.get("declared_unit") or "piece",
        "unitary_product_amount": source.get("unitary_product_amount") or 1,
        "system_boundary": source.get("system_boundary") or "cradle-to-gate",
        "reporting_period_start": source.get("reporting_period_start"),
        "reporting_period_end": source.get("reporting_period_end"),
        "geography_country": source.get("geography_country"),
        "primary_data_share": pds_after,
        "spec_version": source.get("spec_version") or "3.0.0",
        "product_lineage_id": source["product_lineage_id"],
        "version": new_version,
    }

    reporting_year = _reporting_year(source.get("reporting_period_start"))
    line_item_rows = []
    for li in cloned_items:
        row = {
            "product_id": 0,
            "user_id": user_id,
            "component": li.get("component"),
            "material": li.get("material"),
            "spend_usd": li.get("spend_usd"),
            "matched_sector": li.get("matched_sector"),
            "emission_factor": li.get("emission_factor"),
            "ef_source": li.get("ef_source"),
            "kg_co2e": li.get("kg_co2e"),
            "share_pct": li.get("share_pct"),
            "flag_status": li.get("flag_status") or "ok",
            "data_source": li.get("data_source") or "secondary",
            "ef_confidence": li.get("ef_confidence"),
            "country_of_origin": li.get("country_of_origin"),
        }
        row.update(_dqr_fields_for_dict_row(row, reporting_year=reporting_year))
        line_item_rows.append(row)

    aggregate = aggregate_dqr(line_item_rows)
    insert_data["technological_dqr"] = aggregate["technological"]
    insert_data["geographical_dqr"] = aggregate["geographical"]
    insert_data["temporal_dqr"] = aggregate["temporal"]
    insert_data["dqr_computed_at"] = datetime.now(UTC).isoformat()

    client = get_user_client(access_token)
    product_response = client.table("products").insert(insert_data).execute()
    new_product_id = int(product_response.data[0]["product_id"])

    for row in line_item_rows:
        row["product_id"] = new_product_id
    if line_item_rows:
        client.table("line_items").insert(line_item_rows).execute()

    if engagement_id is not None:
        update_engagement(
            engagement_id,
            access_token=access_token,
            primary_kg_co2e=primary_kg_co2e,
            applied_to_product_id=new_product_id,
            pds_before=pds_before,
            pds_after=pds_after,
        )

    return {
        "new_product_id": new_product_id,
        "version": new_version,
        "pds_before": pds_before,
        "pds_after": pds_after,
    }


def _remapped_flag_status(existing_status: str | None, *, has_kg_co2e: bool) -> str:
    parts = [
        part
        for part in (existing_status or "ok").split("|")
        if part and part not in {"low_confidence", "unmatched"}
    ]
    if not has_kg_co2e:
        parts.append("unmatched")
    return "|".join(dict.fromkeys(parts)) if parts else "ok"


def _count_flagged_line_items(items: list[dict]) -> int:
    return sum(1 for li in items if (li.get("flag_status") or "ok") != "ok")


def remap_line_item(
    source_product_id: int,
    item_id: int,
    sector_code: str,
    *,
    user_id: str,
    access_token: str,
) -> dict:
    """Re-map one line item to a chosen sector, creating a new footprint version."""
    source = get_product_by_id(source_product_id, access_token)
    if source is None:
        raise ValueError(f"Source product {source_product_id} not found.")

    source_items = source.get("line_items") or []
    matched = next((li for li in source_items if li.get("item_id") == item_id), None)
    if matched is None:
        raise ValueError(f"Line item {item_id} not found on product {source_product_id}.")

    total_before = float(source.get("total_kg_co2e") or 0.0)
    ef_match = lookup_ef_by_sector_code(
        sector_code,
        matched.get("country_of_origin"),
        material_input=str(matched.get("material") or ""),
        source_citation="Analyst re-map (Open CEDA 2025)",
    )

    spend = matched.get("spend_usd")
    kg_co2e = None
    if spend is not None and spend > 0:
        kg_co2e = round(float(spend) * ef_match.ef_kg_co2e_per_usd, 6)

    cloned_items: list[dict] = []
    for li in source_items:
        row = dict(li)
        if row.get("item_id") == item_id:
            row["matched_sector"] = ef_match.sector_name
            row["emission_factor"] = round(ef_match.ef_kg_co2e_per_usd, 6)
            row["ef_source"] = ef_match.source_citation
            row["ef_confidence"] = ef_match.confidence_score
            row["kg_co2e"] = kg_co2e
            row["data_source"] = "secondary"
            row["flag_status"] = _remapped_flag_status(
                row.get("flag_status"),
                has_kg_co2e=kg_co2e is not None,
            )
        cloned_items.append(row)

    total_kg_co2e = sum(li["kg_co2e"] for li in cloned_items if li.get("kg_co2e") is not None)
    for li in cloned_items:
        kg = li.get("kg_co2e")
        if kg is not None and total_kg_co2e > 0:
            li["share_pct"] = round(kg / total_kg_co2e * 100, 4)
        else:
            li["share_pct"] = None

    flagged_items = _count_flagged_line_items(cloned_items)
    matched_items = sum(1 for li in cloned_items if li.get("kg_co2e") is not None)
    new_version = int(source.get("version") or 1) + 1

    insert_data: dict = {
        "user_id": user_id,
        "product_name": source["product_name"],
        "analysis_date": source["analysis_date"],
        "total_kg_co2e": round(total_kg_co2e, 6),
        "matched_items": matched_items,
        "flagged_items": flagged_items,
        "status": "approved",
        "flagged_comment": source.get("flagged_comment"),
        "product_description": source.get("product_description"),
        "declared_unit": source.get("declared_unit") or "piece",
        "unitary_product_amount": source.get("unitary_product_amount") or 1,
        "system_boundary": source.get("system_boundary") or "cradle-to-gate",
        "reporting_period_start": source.get("reporting_period_start"),
        "reporting_period_end": source.get("reporting_period_end"),
        "geography_country": source.get("geography_country"),
        "primary_data_share": source.get("primary_data_share"),
        "spec_version": source.get("spec_version") or "3.0.0",
        "product_lineage_id": source["product_lineage_id"],
        "version": new_version,
    }

    reporting_year = _reporting_year(source.get("reporting_period_start"))
    line_item_rows = []
    for li in cloned_items:
        row = {
            "product_id": 0,
            "user_id": user_id,
            "component": li.get("component"),
            "material": li.get("material"),
            "spend_usd": li.get("spend_usd"),
            "matched_sector": li.get("matched_sector"),
            "emission_factor": li.get("emission_factor"),
            "ef_source": li.get("ef_source"),
            "kg_co2e": li.get("kg_co2e"),
            "share_pct": li.get("share_pct"),
            "flag_status": li.get("flag_status") or "ok",
            "data_source": li.get("data_source") or "secondary",
            "ef_confidence": li.get("ef_confidence"),
            "country_of_origin": li.get("country_of_origin"),
        }
        row.update(_dqr_fields_for_dict_row(row, reporting_year=reporting_year))
        line_item_rows.append(row)

    aggregate = aggregate_dqr(line_item_rows)
    insert_data["technological_dqr"] = aggregate["technological"]
    insert_data["geographical_dqr"] = aggregate["geographical"]
    insert_data["temporal_dqr"] = aggregate["temporal"]
    insert_data["dqr_computed_at"] = datetime.now(UTC).isoformat()

    client = get_user_client(access_token)
    product_response = client.table("products").insert(insert_data).execute()
    new_product_id = int(product_response.data[0]["product_id"])

    for row in line_item_rows:
        row["product_id"] = new_product_id
    if line_item_rows:
        client.table("line_items").insert(line_item_rows).execute()

    append_audit_log(
        event="line_item_remapped",
        workflow="footprint_lifecycle",
        user_id=user_id,
        access_token=access_token,
        product_name=source.get("product_name"),
        component_name=str(matched.get("material") or ""),
        status=sector_code,
    )

    return {
        "new_product_id": new_product_id,
        "version": new_version,
        "total_kg_co2e_before": round(total_before, 6),
        "total_kg_co2e_after": round(total_kg_co2e, 6),
        "delta_kg_co2e": round(total_kg_co2e - total_before, 6),
        "remapped_item_id": item_id,
        "sector_code": sector_code,
        "sector_name": ef_match.sector_name,
    }


def _line_item_row(
    product_id: int,
    user_id: str,
    li: LineItem,
    *,
    reporting_year: int,
) -> dict:
    flags = []
    if li.is_flagged_by_parser:
        flags.append("parser_flagged")
    if li.is_low_confidence:
        flags.append("low_confidence")
    if li.is_no_ef_match:
        flags.append("unmatched")
    flag_status = "|".join(flags) if flags else "ok"

    row = {
        "product_id": product_id,
        "user_id": user_id,
        "component": li.component,
        "material": li.material,
        "spend_usd": li.spend_usd,
        "matched_sector": li.sector_name or None,
        "emission_factor": round(li.ef_kg_co2e_per_usd, 6) if li.ef_kg_co2e_per_usd else None,
        "ef_source": li.ef_source or None,
        "kg_co2e": round(li.kg_co2e, 6) if li.is_matched else None,
        "share_pct": round(li.share_pct, 4) if li.is_matched else None,
        "flag_status": flag_status,
        "data_source": "secondary",
        "ef_confidence": round(li.ef_confidence, 4) if li.ef_confidence else None,
        "country_of_origin": li.country_of_origin,
    }
    row.update(
        _dqr_fields_for_dict_row(row, reporting_year=reporting_year)
    )
    return row
