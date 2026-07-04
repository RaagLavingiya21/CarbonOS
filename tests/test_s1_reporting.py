"""Inventory report rollup tests — GWP + consolidation multiplier + biogenic memo."""

from __future__ import annotations

import pytest

from s1_calc.gwp import gwp_100
from s1_calc.models import GasMasses
from s1_reporting import build_inventory_report, trace_record
from s1_reporting.report import ReportRecord


def _ng_record(rid: str, multiplier: float, facility_id: str, facility_name: str) -> ReportRecord:
    # 1,000 therms natural gas (research/2.1 example A).
    return ReportRecord(
        record_id=rid,
        gas_masses=GasMasses(kg_co2_fossil=5306.0, kg_ch4=0.100, kg_n2o=0.010),
        multiplier=multiplier,
        facility_id=facility_id,
        facility_name=facility_name,
    )


def test_rollup_applies_multiplier_and_orders_facilities() -> None:
    records = [
        _ng_record("r1", 1.0, "f1", "Plant A"),
        _ng_record("r2", 0.40, "f2", "JV Plant"),
    ]
    report = build_inventory_report(records, "AR5")

    per_record_ar5 = 5306.0 + 0.100 * 28 + 0.010 * 265   # kg
    expected = (per_record_ar5 * 1.0 + per_record_ar5 * 0.40) / 1000.0
    assert report.total_scope1_tco2e == pytest.approx(expected, rel=1e-9)
    assert report.record_count == 2
    # Facilities ordered by contribution, multiplier applied.
    assert [f.facility_id for f in report.by_facility] == ["f1", "f2"]
    assert report.by_facility[0].tco2e > report.by_facility[1].tco2e


def test_biogenic_co2_excluded_from_total_but_reported() -> None:
    records = [
        _ng_record("r1", 1.0, "f1", "Plant A"),
        ReportRecord("r2", GasMasses(kg_co2_biogenic=575.0), 1.0, "f2", "Biomass boiler"),
    ]
    report = build_inventory_report(records, "AR5")
    ng_only = (5306.0 + 0.100 * 28 + 0.010 * 265) / 1000.0
    assert report.total_scope1_tco2e == pytest.approx(ng_only, rel=1e-9)   # biogenic not in total
    assert report.biogenic_co2_tco2e == pytest.approx(0.575, rel=1e-9)     # separate memo


def test_ar_toggle_changes_total_without_new_records() -> None:
    records = [_ng_record("r1", 1.0, "f1", "Plant A")]
    ar5 = build_inventory_report(records, "AR5").total_scope1_tco2e
    ar6 = build_inventory_report(records, "AR6").total_scope1_tco2e
    assert ar5 != ar6
    assert ar6 == pytest.approx((5306.0 + 0.1 * 29.8 + 0.01 * 273) / 1000.0, rel=1e-9)


def test_trace_chain_matches_gwp() -> None:
    rec = _ng_record("r1", 0.5, "f1", "Plant A")
    tr = trace_record(rec, "AR5")
    assert tr["consolidation_multiplier"] == 0.5
    co2 = next(g for g in tr["gases"] if g["gas"].startswith("CO2"))
    assert co2["gwp_100"] == gwp_100("Carbon dioxide", "AR5")
    assert co2["tco2e"] == pytest.approx(5306.0 * 1 * 0.5 / 1000.0, rel=1e-9)
    assert tr["total_tco2e"] == pytest.approx(
        (5306.0 + 0.1 * 28 + 0.01 * 265) * 0.5 / 1000.0, rel=1e-9
    )
