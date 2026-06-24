"""Supabase persistence for product footprint analyses.

No Streamlit imports — callable from any Python context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from calc.footprint import FootprintResult, LineItem
from db.client import get_user_client


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
) -> int:
    """Persist a footprint result. Returns the new product_id."""
    if analysis_date is None:
        analysis_date = date.today()

    client = get_user_client(access_token)
    product_response = (
        client.table("products")
        .insert(
            {
                "user_id": user_id,
                "product_name": product_name.strip(),
                "analysis_date": analysis_date.isoformat(),
                "total_kg_co2e": round(result.total_kg_co2e, 6),
                "matched_items": result.matched_count,
                "flagged_items": result.flagged_count,
                "status": status,
                "flagged_comment": flagged_comment.strip() if flagged_comment else None,
            }
        )
        .execute()
    )
    product_id = product_response.data[0]["product_id"]

    line_item_rows = [_line_item_row(product_id, user_id, li) for li in result.line_items]
    if line_item_rows:
        client.table("line_items").insert(line_item_rows).execute()

    return int(product_id)


def _line_item_row(product_id: int, user_id: str, li: LineItem) -> dict:
    flags = []
    if li.is_flagged_by_parser:
        flags.append("parser_flagged")
    if li.is_low_confidence:
        flags.append("low_confidence")
    if li.is_no_ef_match:
        flags.append("unmatched")
    flag_status = "|".join(flags) if flags else "ok"

    return {
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
    }
