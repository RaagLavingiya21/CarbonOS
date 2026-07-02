"""Map internal product records to WBCSD PACT v3 ProductFootprint payloads."""

from __future__ import annotations

import re
from datetime import date, datetime, timezone

_ISO_COUNTRY = re.compile(r"^[A-Z]{2}$")
_GEOGRAPHY_FIELDS = (
    "geographyRegionOrSubregion",
    "geographyCountry",
    "geographyCountrySubdivision",
)
_DECIMAL_FIELDS = {
    "declaredUnitAmount",
    "productMassPerDeclaredUnit",
    "pcfExcludingBiogenicUptake",
    "pcfIncludingBiogenicUptake",
    "fossilGhgEmissions",
    "fossilCarbonContent",
    "biogenicCarbonContent",
    "exemptedEmissionsPercent",
    "primaryDataShare",
    "technologicalDQR",
    "geographicalDQR",
    "temporalDQR",
}
_MANDATORY_TOP_LEVEL = (
    "id",
    "specVersion",
    "created",
    "status",
    "companyName",
    "companyIds",
    "productDescription",
    "productIds",
    "productNameCompany",
    "pcf",
)
_MANDATORY_PCF = (
    "declaredUnitOfMeasurement",
    "declaredUnitAmount",
    "productMassPerDeclaredUnit",
    "referencePeriodStart",
    "referencePeriodEnd",
    "pcfExcludingBiogenicUptake",
    "pcfIncludingBiogenicUptake",
    "fossilGhgEmissions",
    "fossilCarbonContent",
    "ipccCharacterizationFactors",
    "crossSectoralStandards",
    "exemptedEmissionsPercent",
)


def build_product_footprint(
    product: dict,
    org_name: str | None,
    org_id: str | None,
) -> dict:
    """Map a product row (incl. line_items) to a PACT v3 ProductFootprint dict."""
    analysis_date = _coerce_date(product.get("analysis_date"))
    period_start = _coerce_date(product.get("reporting_period_start"))
    period_end = _coerce_date(product.get("reporting_period_end"))
    if period_start is None or period_end is None:
        year = (analysis_date or date.today()).year
        period_start = date(year, 1, 1)
        period_end = date(year, 12, 31)

    unitary_amount = float(product.get("unitary_product_amount") or 1)
    total_kg = float(product.get("total_kg_co2e") or 0)
    per_unit = total_kg / unitary_amount if unitary_amount else total_kg
    per_unit_str = _decimal_str(per_unit)

    declared_unit = str(product.get("declared_unit") or "piece")
    system_boundary = str(product.get("system_boundary") or "cradle-to-gate")
    boundary_description = (
        f"{system_boundary}; spend-based EEIO screening assessment using Open CEDA 2025 "
        f"(kg CO2e per USD spend)."
    )

    company_id = org_id or str(product.get("user_id") or "")
    company_name = (org_name or "").strip() or "Independent Analyst (CarbonOS)"

    pcf: dict = {
        "declaredUnitOfMeasurement": declared_unit,
        "declaredUnitAmount": _decimal_str(unitary_amount),
        "productMassPerDeclaredUnit": _decimal_str(unitary_amount),
        "referencePeriodStart": _iso_datetime(period_start),
        "referencePeriodEnd": _iso_datetime(period_end),
        "boundaryProcessesDescription": boundary_description,
        "pcfExcludingBiogenicUptake": per_unit_str,
        "pcfIncludingBiogenicUptake": per_unit_str,
        # Spend-based EEIO cannot resolve biogenic/fossil carbon splits.
        "fossilGhgEmissions": per_unit_str,
        "fossilCarbonContent": "0",
        "biogenicCarbonContent": "0",
        "ipccCharacterizationFactors": ["AR6"],
        "crossSectoralStandards": ["GHGP-Product"],
        "exemptedEmissionsPercent": "0",
        "primaryDataShare": _decimal_str(float(product.get("primary_data_share") or 0)),
        "dqi": {
            "technologicalDQR": "4",
            "geographicalDQR": "4",
            "temporalDQR": "4",
        },
        "secondaryEmissionFactorSources": [
            {"name": "Open CEDA 2025", "version": "2025"},
        ],
    }

    geography_country = product.get("geography_country")
    if geography_country:
        pcf["geographyCountry"] = str(geography_country).upper()

    product_id = product.get("product_id")
    footprint_uuid = product.get("footprint_uuid")
    if footprint_uuid is None:
        raise ValueError("product.footprint_uuid is required for PACT export")

    description = (product.get("product_description") or "").strip()
    if not description:
        description = str(product.get("product_name") or "")

    payload = {
        "id": str(footprint_uuid),
        "specVersion": str(product.get("spec_version") or "3.0.0"),
        "created": _iso_datetime_from_timestamp(product.get("created_at"), fallback=analysis_date),
        "status": "Active",
        "companyName": company_name,
        "companyIds": [f"urn:pfa:company:{company_id}"],
        "productDescription": description,
        "productIds": [f"urn:pfa:product:{product_id}"],
        "productNameCompany": str(product.get("product_name") or ""),
        "pcf": pcf,
    }
    return payload


def validate_product_footprint(payload: dict) -> list[str]:
    """Return a list of violations (empty = valid).

    Checks mandatory fields, decimal-as-string formatting, and geography mutual exclusivity.
    """
    violations: list[str] = []

    for field in _MANDATORY_TOP_LEVEL:
        if field not in payload or payload[field] in (None, ""):
            violations.append(f"Missing mandatory field: {field}")

    pcf = payload.get("pcf")
    if not isinstance(pcf, dict):
        violations.append("Missing or invalid pcf object")
        return violations

    for field in _MANDATORY_PCF:
        if field not in pcf or pcf[field] in (None, ""):
            violations.append(f"Missing mandatory pcf field: {field}")

    violations.extend(_validate_decimal_strings(payload))
    violations.extend(_validate_geography_mutual_exclusivity(pcf))

    dqi = pcf.get("dqi")
    if isinstance(dqi, dict):
        for field in ("technologicalDQR", "geographicalDQR", "temporalDQR"):
            value = dqi.get(field)
            if value is None:
                violations.append(f"Missing mandatory dqi field: {field}")
            elif not isinstance(value, str):
                violations.append(f"dqi.{field} must be a decimal string")
    else:
        violations.append("Missing or invalid pcf.dqi object")

    geography_country = pcf.get("geographyCountry")
    if geography_country is not None and not _ISO_COUNTRY.match(str(geography_country)):
        violations.append("pcf.geographyCountry must be ISO 3166-1 alpha-2 uppercase")

    return violations


def _validate_decimal_strings(payload: dict) -> list[str]:
    violations: list[str] = []
    pcf = payload.get("pcf") or {}

    for field in (
        "declaredUnitAmount",
        "productMassPerDeclaredUnit",
        "pcfExcludingBiogenicUptake",
        "pcfIncludingBiogenicUptake",
        "fossilGhgEmissions",
        "fossilCarbonContent",
        "exemptedEmissionsPercent",
        "primaryDataShare",
    ):
        value = pcf.get(field)
        if value is not None and not isinstance(value, str):
            violations.append(f"pcf.{field} must be serialized as a string")

    dqi = pcf.get("dqi") or {}
    for field in ("technologicalDQR", "geographicalDQR", "temporalDQR"):
        value = dqi.get(field)
        if value is not None and not isinstance(value, str):
            violations.append(f"pcf.dqi.{field} must be serialized as a string")

    return violations


def _validate_geography_mutual_exclusivity(pcf: dict) -> list[str]:
    present = [field for field in _GEOGRAPHY_FIELDS if pcf.get(field) not in (None, "")]
    if len(present) > 1:
        return [f"Geography fields are mutually exclusive; found: {', '.join(present)}"]
    return []


def _decimal_str(value: float) -> str:
    if value == 0:
        return "0"
    if float(value).is_integer():
        return str(int(value))
    text = format(float(value), ".15g")
    return text


def _coerce_date(value: object | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    return None


def _iso_datetime(value: date | datetime) -> str:
    if isinstance(value, datetime):
        dt = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    else:
        dt = datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _iso_datetime_from_timestamp(value: object | None, *, fallback: date | None) -> str:
    if isinstance(value, str):
        if "T" in value:
            return value if value.endswith("Z") else f"{value}Z"
        parsed = date.fromisoformat(value[:10])
        return _iso_datetime(parsed)
    if isinstance(value, datetime):
        return _iso_datetime(value)
    if fallback is not None:
        return _iso_datetime(fallback)
    return _iso_datetime(date.today())
