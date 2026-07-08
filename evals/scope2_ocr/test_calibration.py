"""Tests for the pure REVIEW_THRESHOLD calibration math (no API)."""

from __future__ import annotations

from datetime import date

from evals.scope2_ocr.calibration import (
    Observation,
    observations_from_rows,
    recommend_threshold,
    sweep_threshold,
)
from s2_ingestion.ocr import ExtractedMeterRow

# Two low-confidence wrong reads, two high-confidence correct reads: a threshold
# near 0.71 catches both wrong reads without flagging the correct ones.
_OBS = [
    Observation(0.60, meter_wrong=True),
    Observation(0.70, meter_wrong=True),
    Observation(0.97, meter_wrong=False),
    Observation(0.98, meter_wrong=False),
]


def test_sweep_precision_recall_at_key_cutoffs() -> None:
    by_t = {round(p.threshold, 2): p for p in sweep_threshold(_OBS)}
    # At 0.60 neither wrong read (conf 0.60, 0.70) is below the cutoff -> nothing
    # flagged, so both misreads are missed (recall 0).
    assert (by_t[0.60].tp, by_t[0.60].fn) == (0, 2)
    assert by_t[0.60].recall == 0.0
    # At 0.71 both wrong reads are flagged, correct ones are not.
    p71 = by_t[0.71]
    assert (p71.tp, p71.fp, p71.fn) == (2, 0, 0)
    assert p71.precision == 1.0 and p71.recall == 1.0
    # At 0.99 the correct reads get swept in too -> precision drops.
    p99 = by_t[0.99]
    assert p99.tp == 2 and p99.fp == 2
    assert p99.precision < 1.0 and p99.recall == 1.0


def test_recall_is_monotonic_nondecreasing_in_threshold() -> None:
    points = sweep_threshold(_OBS)
    recalls = [p.recall for p in points]
    assert recalls == sorted(recalls)


def test_recommend_picks_smallest_cutoff_meeting_recall_floor() -> None:
    # Smallest cutoff catching both wrong reads is just above 0.70 -> 0.71.
    assert recommend_threshold(_OBS, min_recall=0.95) == 0.71


def test_recommend_falls_back_to_best_recall_when_floor_unreachable() -> None:
    # A wrong read at very high confidence can't be caught without also flagging
    # everything; with an impossible floor we still return a real grid point.
    obs = [Observation(0.999, meter_wrong=True), Observation(0.5, meter_wrong=False)]
    t = recommend_threshold(obs, min_recall=1.0)
    assert 0.50 <= t <= 0.99


def test_review_reason_forces_flag_regardless_of_confidence() -> None:
    # A high-confidence read with a parse/normalize reason is always flagged.
    obs = [Observation(0.99, meter_wrong=True, has_review_reason=True)]
    p = sweep_threshold(obs, grid=[0.50])[0]
    assert (p.tp, p.fp, p.fn) == (1, 0, 0)


def _row(
    *, quantity: float, min_conf: float, reasons: list[str] | None = None
) -> ExtractedMeterRow:
    return ExtractedMeterRow(
        meter_number="MTR-1",
        energy_carrier="electricity",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        raw_quantity=quantity,
        raw_unit="kWh",
        canonical_mwh=quantity / 1000,
        cost_usd=None,
        demand_kw=None,
        is_estimated_read=False,
        is_cost_only=False,
        conversion_note=None,
        min_confidence=min_conf,
        review_reasons=reasons or [],
    )


def test_observations_from_rows_marks_wrong_and_reasons() -> None:
    label = {
        "meters": [
            {
                "energy_carrier": "electricity",
                "service_period_start": "2025-01-01",
                "service_period_end": "2025-01-31",
                "consumption_quantity": 1500,
                "consumption_unit": "kWh",
                "is_estimated_read": False,
            }
        ]
    }
    # Correct quantity, high confidence -> not wrong, not forced.
    good = observations_from_rows([_row(quantity=1500, min_conf=0.95)], label)[0]
    assert good.meter_wrong is False and good.has_review_reason is False
    # Wrong quantity -> meter_wrong True.
    bad = observations_from_rows([_row(quantity=9999, min_conf=0.95)], label)[0]
    assert bad.meter_wrong is True
    # Parse reason present -> has_review_reason True.
    flagged = observations_from_rows(
        [_row(quantity=1500, min_conf=0.95, reasons=["bad date"])], label
    )[0]
    assert flagged.has_review_reason is True
