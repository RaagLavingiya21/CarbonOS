"""Tests for the Epic G disclosure datapoint mapper (s3_disclosure/). Pure logic.

Invariants: numbers are looked up from the inventory (never generated) with a
source_ref; SB253 is provisional; missing inputs are flagged, not faked;
format_version recorded; determinism.
"""

from __future__ import annotations

import pytest

from s3_disclosure.mapper import DisclosureSpecError, available_frameworks, map_disclosure
from s3_disclosure.serialize import to_csv, to_markdown

_INV = {"total": 100000.0, "categories": {1: 70000.0, 4: 12000.0, 6: 8000.0}}


def test_frameworks_available():
    assert set(available_frameworks()) == {"esrs_e1", "sb253", "ifrs_s2"}


def test_scope3_total_looked_up_and_converted_to_tonnes():
    r = map_disclosure(_INV, "esrs_e1")
    dp = next(d for d in r.datapoints if d.key == "E1-6_gross_scope3")
    assert dp.value == 100.0  # 100000 kg -> 100 tCO2e
    assert dp.unit == "tCO2e"
    assert dp.source_ref and "inventory:total" in dp.source_ref


def test_every_numeric_datapoint_has_a_source():
    for fw in available_frameworks():
        r = map_disclosure(_INV, fw)
        for dp in list(r.datapoints) + list(r.category_breakdown):
            if dp.value is not None:
                assert dp.source_ref, f"{fw}:{dp.key} numeric without source"


def test_methodology_is_text_not_a_number():
    r = map_disclosure(_INV, "ifrs_s2")
    meth = next(d for d in r.datapoints if "methodology" in d.key)
    assert meth.value is None and meth.text and "GHG Protocol" in meth.text
    assert meth.source_ref is None


def test_sb253_is_provisional():
    r = map_disclosure(_INV, "sb253")
    assert r.is_provisional is True
    assert any("provisional" in n.lower() for n in r.notes)
    assert "PROVISIONAL" in to_markdown(r)


def test_esrs_has_category_breakdown_others_do_not():
    assert map_disclosure(_INV, "esrs_e1").category_breakdown  # non-empty
    assert map_disclosure(_INV, "ifrs_s2").category_breakdown == []


def test_missing_total_is_flagged_not_faked():
    r = map_disclosure({"total": None, "categories": {}}, "esrs_e1")
    dp = next(d for d in r.datapoints if d.key == "E1-6_gross_scope3")
    assert dp.value is None and dp.flag == "missing"


def test_format_version_recorded():
    assert map_disclosure(_INV, "esrs_e1").format_version == "v1-2026"


def test_unknown_framework_raises():
    with pytest.raises(DisclosureSpecError):
        map_disclosure(_INV, "tcfd")


def test_csv_and_markdown_render():
    r = map_disclosure(_INV, "esrs_e1")
    assert "E1-6_gross_scope3" in to_csv(r)
    assert "Gross Scope 3" in to_markdown(r)


def test_determinism():
    assert to_markdown(map_disclosure(_INV, "esrs_e1")) == to_markdown(
        map_disclosure(_INV, "esrs_e1")
    )
