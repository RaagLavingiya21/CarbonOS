"""Tests for the Epic G disclosure route's DB-free helpers (end-to-end mapping
from stored inventory rows to a framework disclosure, without a live DB)."""

from __future__ import annotations

from api.routes.scope3_disclosure import inventory_from_rows
from s3_disclosure.mapper import map_disclosure
from s3_disclosure.serialize import to_markdown

# Shapes as they come back from db.s3_inventory_store.
_VERSION = {"inventory_id": 7, "total_kg_co2e": 100000.0, "status": "locked"}
_CATEGORY_ROWS = [
    {"scope3_category": 1, "total_kg_co2e": 70000.0, "method": "spend"},
    {"scope3_category": 4, "total_kg_co2e": 12000.0, "method": "spend"},
    {"scope3_category": 6, "total_kg_co2e": 8000.0, "method": "spend"},
]


def test_inventory_from_rows_shape():
    inv = inventory_from_rows(_VERSION, _CATEGORY_ROWS)
    assert inv["total"] == 100000.0
    assert inv["categories"] == {1: 70000.0, 4: 12000.0, 6: 8000.0}


def test_end_to_end_esrs_disclosure_from_rows():
    inv = inventory_from_rows(_VERSION, _CATEGORY_ROWS)
    result = map_disclosure(inv, "esrs_e1")
    total_dp = next(d for d in result.datapoints if d.key == "E1-6_gross_scope3")
    assert total_dp.value == 100.0  # 100000 kg -> 100 tCO2e
    assert result.category_breakdown  # ESRS includes the breakdown
    assert "Gross Scope 3" in to_markdown(result)


def test_sb253_from_rows_is_provisional():
    inv = inventory_from_rows(_VERSION, _CATEGORY_ROWS)
    result = map_disclosure(inv, "sb253")
    assert result.is_provisional is True


def test_null_total_maps_without_faking():
    inv = inventory_from_rows({"total_kg_co2e": None}, [])
    result = map_disclosure(inv, "esrs_e1")
    total_dp = next(d for d in result.datapoints if d.key == "E1-6_gross_scope3")
    assert total_dp.value is None and total_dp.flag == "missing"
