"""Portfolio health signals — pure business logic, no DB/UI imports."""

from __future__ import annotations

from datetime import date


def _reporting_end_year(product: dict) -> int | None:
    end = product.get("reporting_period_end")
    if end is None:
        return None
    if isinstance(end, date):
        return end.year
    return date.fromisoformat(str(end)[:10]).year


def _aggregate_dqr_mean(product: dict) -> float | None:
    values = [
        product.get("technological_dqr"),
        product.get("geographical_dqr"),
        product.get("temporal_dqr"),
    ]
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


def footprint_health(product: dict) -> dict:
    """Return health status and human-readable reasons for a footprint row."""
    reasons: list[str] = []
    current_year = date.today().year

    end_year = _reporting_end_year(product)
    if end_year is not None and end_year < current_year:
        reasons.append(f"Reporting period ended in {end_year} (stale vs {current_year}).")

    if product.get("status") == "flagged":
        reasons.append("Footprint status is flagged.")

    if (product.get("flagged_items") or 0) > 0:
        reasons.append("One or more line items are flagged for review.")

    pds = product.get("primary_data_share")
    if pds is not None and float(pds) == 0.0:
        reasons.append("Primary data share is 0% (screening-grade secondary data only).")

    for dimension, label in (
        ("technological_dqr", "technological"),
        ("geographical_dqr", "geographical"),
        ("temporal_dqr", "temporal"),
    ):
        value = product.get(dimension)
        if value is not None and int(value) >= 4:
            reasons.append(f"Aggregate {label} DQR is {value} (≥ 4).")

    if end_year is not None and end_year < current_year:
        status = "stale"
    elif reasons:
        status = "attention"
    else:
        status = "healthy"

    return {"status": status, "reasons": reasons}
