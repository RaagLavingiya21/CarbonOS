"""Tests for the Epic E progress engine (s3_progress/). Pure logic.

Headline invariant: a change driven only by an EF-version/method switch decomposes
to ZERO real reduction (never claimed as progress). Also covers on/off-track,
base-year recalc thresholds, and narrative grounding.
"""

from __future__ import annotations

from s3_progress.decompose import decompose
from s3_progress.models import CategoryPoint, InventorySnapshot
from s3_progress.narrative import build_progress_narrative
from s3_progress.tracker import evaluate_recalc, track_progress


def _snap(year, cats):
    return InventorySnapshot(
        reporting_year=year,
        categories=[CategoryPoint(c, kg, method=m, ef_version=v) for c, kg, m, v in cats],
    )


# --- decomposition (real vs method) -----------------------------------------


def test_real_reduction_counts():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025"), (4, 200, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 800, "spend", "CEDA-2025"), (4, 200, "spend", "CEDA-2025")])
    d = decompose(base, curr)
    assert d.real_delta == -200  # genuine 200 kg cut in Cat 1
    assert d.method_delta == 0


def test_ef_version_change_is_not_a_real_reduction():
    """The headline invariant: switching EF library version yields 0 real delta."""
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 700, "spend", "CEDA-2026")])  # only the EF version changed
    d = decompose(base, curr)
    assert d.real_delta == 0
    assert d.method_delta == -300
    assert d.category_deltas[0].reason == "ef_version_change"


def test_method_switch_is_method_delta():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 600, "activity", "CEDA-2025")])
    d = decompose(base, curr)
    assert d.real_delta == 0
    assert d.method_delta == -400
    assert d.category_deltas[0].reason == "method_change"


def test_new_category_is_completeness_not_a_rise():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 1000, "spend", "CEDA-2025"), (6, 150, "spend", "CEDA-2025")])
    d = decompose(base, curr)
    assert d.real_delta == 0
    assert d.method_delta == 150  # newly measured, not a real increase


# --- progress vs trajectory -------------------------------------------------


def test_on_track_uses_real_total_only():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 800, "spend", "CEDA-2025")])  # real -200
    d = decompose(base, curr)
    p = track_progress(d, base_total_kg=1000, trajectory={2026: 850})
    assert p.real_total_kg == 800
    assert p.on_track is True


def test_off_track_when_real_total_above_target():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 950, "spend", "CEDA-2025")])  # real -50
    d = decompose(base, curr)
    p = track_progress(d, base_total_kg=1000, trajectory={2026: 850})
    assert p.on_track is False


def test_method_change_does_not_create_false_progress():
    """An EF-version drop must NOT show as being on-track."""
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 700, "spend", "CEDA-2026")])  # method-only -300
    d = decompose(base, curr)
    p = track_progress(d, base_total_kg=1000, trajectory={2026: 850})
    assert p.real_total_kg == 1000  # like-for-like unchanged
    assert p.on_track is False
    assert any("method" in n.lower() for n in p.notes)


def test_no_trajectory_target_is_undetermined():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 900, "spend", "CEDA-2025")])
    p = track_progress(decompose(base, curr), base_total_kg=1000, trajectory={})
    assert p.on_track is None


# --- base-year recalc -------------------------------------------------------


def test_recalc_required_above_threshold():
    r = evaluate_recalc("ma", 0.12)
    assert r.recalc_required is True


def test_no_recalc_below_threshold():
    r = evaluate_recalc("ma", 0.02)
    assert r.recalc_required is False


def test_organic_change_never_recalcs():
    r = evaluate_recalc("organic", 0.50)
    assert r.recalc_required is False


# --- narrative --------------------------------------------------------------


def test_narrative_claims_real_only_and_flags_method():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 700, "spend", "CEDA-2026")])  # method-only
    d = decompose(base, curr)
    p = track_progress(d, base_total_kg=1000, trajectory={2026: 850})
    text = build_progress_narrative(d, p)
    assert "held flat" in text  # real change is zero
    assert "method" in text.lower()


def test_determinism():
    base = _snap(2025, [(1, 1000, "spend", "CEDA-2025")])
    curr = _snap(2026, [(1, 800, "spend", "CEDA-2025")])
    assert decompose(base, curr).real_delta == decompose(base, curr).real_delta
