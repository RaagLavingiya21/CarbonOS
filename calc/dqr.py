"""Data Quality Rating (DQR) computation — pure business logic, no DB/UI imports.

PACT convention: 1 = best, 5 = worst.
"""

from __future__ import annotations

CEDA_VINTAGE_YEAR = 2025


def line_item_dqr(
    *,
    ef_confidence: float | None,
    is_low_confidence: bool,
    data_source: str | None,
    country_of_origin: str | None,
    reporting_year: int,
) -> dict[str, int]:
    """Return per-line technological, geographical, and temporal DQR (1–5)."""
    if data_source == "primary":
        technological = 1
    else:
        confidence = float(ef_confidence or 0.0)
        if is_low_confidence or confidence < 60:
            technological = 5
        elif confidence >= 90:
            technological = 2
        elif confidence >= 75:
            technological = 3
        elif confidence >= 60:
            technological = 4
        else:
            technological = 5

    country = (country_of_origin or "").strip()
    geographical = 2 if country else 4

    year_gap = abs(reporting_year - CEDA_VINTAGE_YEAR)
    if year_gap <= 1:
        temporal = 1
    elif year_gap <= 3:
        temporal = 2
    elif year_gap <= 5:
        temporal = 3
    else:
        temporal = 4

    return {
        "technological": technological,
        "geographical": geographical,
        "temporal": temporal,
    }


def aggregate_dqr(line_items: list[dict]) -> dict[str, int]:
    """Kg CO₂e-weighted mean per dimension over matched lines; simple mean if total is 0."""
    matched = [
        li
        for li in line_items
        if li.get("kg_co2e") is not None
        and li.get("technological_dqr") is not None
        and li.get("geographical_dqr") is not None
        and li.get("temporal_dqr") is not None
    ]
    if not matched:
        return {"technological": 5, "geographical": 4, "temporal": 4}

    total_kg = sum(float(li["kg_co2e"]) for li in matched)
    if total_kg <= 0:
        tech = round(sum(li["technological_dqr"] for li in matched) / len(matched))
        geo = round(sum(li["geographical_dqr"] for li in matched) / len(matched))
        temp = round(sum(li["temporal_dqr"] for li in matched) / len(matched))
        return {
            "technological": int(tech),
            "geographical": int(geo),
            "temporal": int(temp),
        }

    tech = sum(float(li["kg_co2e"]) * li["technological_dqr"] for li in matched) / total_kg
    geo = sum(float(li["kg_co2e"]) * li["geographical_dqr"] for li in matched) / total_kg
    temp = sum(float(li["kg_co2e"]) * li["temporal_dqr"] for li in matched) / total_kg
    return {
        "technological": int(round(tech)),
        "geographical": int(round(geo)),
        "temporal": int(round(temp)),
    }
