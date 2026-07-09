"""DB-free tests for the Epic E progress route helpers: build snapshots from
stored inventory rows and run the real-vs-method decomposition end-to-end."""

from __future__ import annotations

from api.routes.scope3_progress import snapshot_from_rows
from s3_progress.decompose import decompose
from s3_progress.tracker import track_progress


def _rows(year, cats):
    version = {"reporting_year": year, "total_kg_co2e": sum(k for _, k, _ in cats)}
    rows = [{"scope3_category": c, "total_kg_co2e": k, "method": m} for c, k, m in cats]
    return version, rows


def test_snapshot_from_rows():
    version, rows = _rows(2025, [(1, 1000, "spend"), (4, 200, "spend")])
    snap = snapshot_from_rows(version, rows)
    assert snap.reporting_year == 2025
    assert snap.total_kg_co2e == 1200
    assert snap.by_category[1].method == "spend"


def test_end_to_end_real_reduction():
    bv, br = _rows(2025, [(1, 1000, "spend")])
    cv, cr = _rows(2026, [(1, 800, "spend")])
    base, current = snapshot_from_rows(bv, br), snapshot_from_rows(cv, cr)
    d = decompose(base, current)
    p = track_progress(d, base.total_kg_co2e, {2026: 850})
    assert d.real_delta == -200
    assert p.on_track is True


def test_method_switch_not_counted_as_real():
    bv, br = _rows(2025, [(1, 1000, "spend")])
    cv, cr = _rows(2026, [(1, 600, "product_rollup")])  # method changed
    base, current = snapshot_from_rows(bv, br), snapshot_from_rows(cv, cr)
    d = decompose(base, current)
    assert d.real_delta == 0
    assert d.method_delta == -400
