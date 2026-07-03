from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import jsonschema
import pytest

from exchange.pact import build_product_footprint, validate_product_footprint

SCHEMA_PATH = Path(__file__).resolve().parent / "fixtures" / "pact_v3_product_footprint_schema.json"


@pytest.fixture
def pact_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def _sample_product(**overrides: object) -> dict:
    product = {
        "product_id": 42,
        "user_id": "00000000-0000-0000-0000-000000000099",
        "product_name": "Clean T-Shirt",
        "product_description": "Organic cotton crew neck t-shirt",
        "analysis_date": "2025-06-15",
        "total_kg_co2e": 12.5,
        "matched_items": 5,
        "flagged_items": 0,
        "status": "approved",
        "footprint_uuid": str(uuid4()),
        "declared_unit": "piece",
        "unitary_product_amount": 1.0,
        "system_boundary": "cradle-to-gate",
        "reporting_period_start": "2025-01-01",
        "reporting_period_end": "2025-12-31",
        "geography_country": None,
        "primary_data_share": 0.0,
        "spec_version": "3.0.0",
        "version": 1,
        "created_at": "2025-06-15T10:00:00Z",
        "updated_at": "2025-06-15T10:00:00Z",
        "line_items": [],
    }
    product.update(overrides)
    return product


def test_build_product_footprint_validates_against_vendored_schema(pact_schema: dict) -> None:
    product = _sample_product()
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")

    jsonschema.validate(instance=payload, schema=pact_schema)


def test_all_decimal_fields_are_strings() -> None:
    product = _sample_product(total_kg_co2e=10.5, unitary_product_amount=2.0, primary_data_share=0.0)
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")
    pcf = payload["pcf"]

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
        assert isinstance(pcf[field], str), field

    for field in ("technologicalDQR", "geographicalDQR", "temporalDQR"):
        assert isinstance(pcf["dqi"][field], str), field


def test_geography_country_none_omits_geography_keys() -> None:
    payload = build_product_footprint(
        _sample_product(geography_country=None),
        org_name="Acme Corp",
        org_id="org-123",
    )
    pcf = payload["pcf"]
    assert "geographyCountry" not in pcf
    assert "geographyRegionOrSubregion" not in pcf
    assert "geographyCountrySubdivision" not in pcf


def test_geography_country_us_sets_only_country() -> None:
    payload = build_product_footprint(
        _sample_product(geography_country="US"),
        org_name="Acme Corp",
        org_id="org-123",
    )
    pcf = payload["pcf"]
    assert pcf["geographyCountry"] == "US"
    assert "geographyRegionOrSubregion" not in pcf
    assert "geographyCountrySubdivision" not in pcf


def test_primary_data_share_zero_serializes_as_string_zero() -> None:
    payload = build_product_footprint(
        _sample_product(primary_data_share=0.0),
        org_name="Acme Corp",
        org_id="org-123",
    )
    assert payload["pcf"]["primaryDataShare"] == "0"


def test_primary_data_share_non_zero_serializes_and_validates(pact_schema: dict) -> None:
    product = _sample_product(primary_data_share=0.35)
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")
    assert payload["pcf"]["primaryDataShare"] == "0.35"
    jsonschema.validate(instance=payload, schema=pact_schema)


def test_validate_product_footprint_catches_missing_mandatory_field() -> None:
    product = _sample_product()
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")
    broken = deepcopy(payload)
    del broken["companyName"]

    violations = validate_product_footprint(broken)
    assert any("companyName" in violation for violation in violations)


def test_total_per_unit_emissions_math() -> None:
    product = _sample_product(total_kg_co2e=20.0, unitary_product_amount=4.0)
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")
    pcf = payload["pcf"]

    assert pcf["pcfExcludingBiogenicUptake"] == "5"
    assert pcf["fossilGhgEmissions"] == "5"


def test_small_footprint_does_not_serialize_as_scientific_notation(pact_schema: dict) -> None:
    # A small per-unit footprint (routine for a low-spend line item, since kg_co2e is
    # already rounded to 6 decimal places in db/store.py) must still serialize as plain
    # decimal notation - the PACT Decimal pattern (^[+-]?\d+(\.\d+)?$) rejects "4e-06".
    product = _sample_product(total_kg_co2e=0.000004, unitary_product_amount=1.0)
    payload = build_product_footprint(product, org_name="Acme Corp", org_id="org-123")
    pcf = payload["pcf"]

    assert pcf["pcfExcludingBiogenicUptake"] == "0.000004"
    assert "e" not in pcf["pcfExcludingBiogenicUptake"].lower()
    jsonschema.validate(instance=payload, schema=pact_schema)
