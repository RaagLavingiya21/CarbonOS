"""Tests for Scope 2 estimated-read / true-up dedup (PRD 5.6)."""

from __future__ import annotations

from s2_ingestion.dedup import BillKey, resolve_supersessions


def _bill(
    bill_id: int,
    *,
    account: int = 1,
    start: str = "2025-01-01",
    end: str = "2025-01-31",
    estimated: bool = False,
    cost_only: bool = False,
) -> BillKey:
    return BillKey(
        bill_id=bill_id,
        account_id=account,
        period_start=start,
        period_end=end,
        is_estimated_read=estimated,
        is_cost_only=cost_only,
    )


def test_actual_supersedes_estimate_same_period() -> None:
    estimate = _bill(1, estimated=True)
    actual = _bill(2)
    assert resolve_supersessions([estimate, actual]) == [(1, 2)]


def test_late_estimate_is_superseded_by_standing_actual() -> None:
    # Estimate arrives (higher bill_id) after the actual — the actual still wins.
    actual = _bill(1)
    late_estimate = _bill(2, estimated=True)
    assert resolve_supersessions([actual, late_estimate]) == [(2, 1)]


def test_reissued_actual_supersedes_prior_actual() -> None:
    # Two actuals for one period = a correction; the later insert (max id) wins.
    assert resolve_supersessions([_bill(1), _bill(2)]) == [(1, 2)]


def test_cost_only_is_weakest() -> None:
    cost = _bill(1, cost_only=True)
    estimate = _bill(2, estimated=True)
    actual = _bill(3)
    pairs = set(resolve_supersessions([cost, estimate, actual]))
    assert pairs == {(1, 3), (2, 3)}


def test_different_periods_are_never_merged() -> None:
    jan = _bill(1, start="2025-01-01", end="2025-01-31", estimated=True)
    feb = _bill(2, start="2025-02-01", end="2025-02-28")
    assert resolve_supersessions([jan, feb]) == []


def test_different_accounts_are_never_merged() -> None:
    a = _bill(1, account=1, estimated=True)
    b = _bill(2, account=2)
    assert resolve_supersessions([a, b]) == []


def test_single_bill_and_empty_are_noops() -> None:
    assert resolve_supersessions([]) == []
    assert resolve_supersessions([_bill(1)]) == []


def test_idempotent_after_supersession_removed() -> None:
    # Once the loser is superseded (excluded), re-running over the survivor is a no-op.
    survivor = _bill(2)
    assert resolve_supersessions([survivor]) == []
