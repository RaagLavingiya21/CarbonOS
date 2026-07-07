"""Tests for Scope 2 utility-bill OCR extraction (PRD 5.1)."""

from __future__ import annotations

from datetime import date

from s2_ingestion.ocr import (
    REVIEW_THRESHOLD,
    BillExtraction,
    extract_bill_document,
    normalize_bill,
    normalize_meter,
    parse_extraction,
)


def _f(value, confidence=0.98) -> dict:
    return {"value": value, "confidence": confidence}


def _meter(**overrides) -> dict:
    meter = {
        "meter_number": _f("MTR-1"),
        "energy_carrier": _f("Electricity"),
        "service_period_start": _f("2025-01-01"),
        "service_period_end": _f("2025-01-31"),
        "consumption_quantity": _f("1500"),
        "consumption_unit": _f("kWh"),
        "demand_kw": _f("42"),
        "total_cost_usd": _f("$210.50"),
        "is_estimated_read": _f("false"),
    }
    meter.update(overrides)
    return meter


def _bill(meters, **header) -> dict:
    return {
        "utility_name": _f(header.get("utility_name", "PG&E")),
        "account_number": _f(header.get("account_number", "1234567")),
        "service_address": _f(header.get("service_address", "1 Main St")),
        "meters": meters,
    }


def _invoke_returning(payload):
    return lambda prompt, media_type, b64: payload


# --- parsing ---------------------------------------------------------------


def test_parse_extraction_builds_header_and_meters() -> None:
    ext = parse_extraction(_bill([_meter()]))
    assert ext.header["utility_name"].value == "PG&E"
    assert len(ext.meters) == 1
    assert ext.meters[0].get("consumption_unit").value == "kWh"


def test_confidence_zeroed_for_absent_value_and_clamped() -> None:
    ext = parse_extraction(_bill([_meter(meter_number=_f(None, 0.9), demand_kw=_f("5", 5.0))]))
    meter = ext.meters[0]
    assert meter.get("meter_number").confidence == 0.0  # null value -> confidence 0
    assert meter.get("demand_kw").confidence == 1.0  # clamped from 5.0


# --- normalization ---------------------------------------------------------


def test_electricity_meter_normalizes_to_mwh() -> None:
    row = normalize_meter(parse_extraction(_bill([_meter()])).meters[0])
    assert row.canonical_mwh == 1.5
    assert row.energy_carrier == "electricity"
    assert row.period_start == date(2025, 1, 1)
    assert row.cost_usd == 210.5
    assert row.is_cost_only is False
    assert row.needs_review is False


def test_gas_therms_normalize() -> None:
    meter = _meter(energy_carrier=_f("Natural Gas"), consumption_quantity=_f("1000"), consumption_unit=_f("therms"))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.energy_carrier == "natural_gas"
    assert row.canonical_mwh is not None and row.canonical_mwh > 0


def test_ambiguous_gas_unit_flags_review_not_crash() -> None:
    # CCF is a volume, not energy — normalize refuses it; must flag, never assume.
    meter = _meter(energy_carrier=_f("Gas"), consumption_unit=_f("CCF"))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.canonical_mwh is None
    assert row.needs_review is True
    assert any("CCF" in r for r in row.review_reasons)


def test_estimated_read_flag_parsed() -> None:
    meter = _meter(is_estimated_read=_f("true"))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.is_estimated_read is True


def test_cost_only_when_quantity_absent() -> None:
    meter = _meter(consumption_quantity=_f(None, 0.0), consumption_unit=_f(None, 0.0))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.is_cost_only is True
    assert row.canonical_mwh is None


def test_low_confidence_critical_field_routes_to_review() -> None:
    meter = _meter(consumption_quantity=_f("1500", REVIEW_THRESHOLD - 0.2))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.needs_review is True


def test_missing_critical_field_flags_reason() -> None:
    meter = _meter(service_period_end=_f(None, 0.0))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.needs_review is True
    assert any("service_period_end" in r for r in row.review_reasons)


def test_unrecognized_carrier_flagged() -> None:
    meter = _meter(energy_carrier=_f("plutonium"))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.energy_carrier is None
    assert any("plutonium" in r for r in row.review_reasons)


def test_alt_date_format_parses() -> None:
    meter = _meter(service_period_start=_f("Jan 01, 2025"), service_period_end=_f("01/31/2025"))
    row = normalize_meter(parse_extraction(_bill([meter])).meters[0])
    assert row.period_start == date(2025, 1, 1)
    assert row.period_end == date(2025, 1, 31)


# --- multi-meter + document flow -------------------------------------------


def test_multi_meter_bill_yields_row_per_meter() -> None:
    elec = _meter()
    gas = _meter(energy_carrier=_f("Natural Gas"), consumption_unit=_f("therms"), meter_number=_f("MTR-2"))
    rows = normalize_bill(parse_extraction(_bill([elec, gas])))
    assert len(rows) == 2
    assert {r.energy_carrier for r in rows} == {"electricity", "natural_gas"}


def test_extract_bill_document_uses_injected_invoke() -> None:
    ext = extract_bill_document(b"%PDF-fake", "application/pdf", invoke=_invoke_returning(_bill([_meter()])))
    assert isinstance(ext, BillExtraction)
    assert ext.error is None
    assert len(ext.meters) == 1


def test_extract_bill_document_flags_llm_failure() -> None:
    def _boom(prompt, media_type, b64):
        raise RuntimeError("vision timeout")

    ext = extract_bill_document(b"x", "image/png", invoke=_boom)
    assert ext.error == "vision timeout"
    assert ext.meters == []
