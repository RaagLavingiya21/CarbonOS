"""Estimated-read / true-up de-duplication (PRD 5.6 immutability).

Utilities issue an *estimated* meter read for a period, then a later bill *trues it
up* with the actual read for the same period. A cost-only row is a weaker signal
still. Without dedup the estimate and its true-up both feed the calc engine and the
period's consumption is double-counted.

This module is the pure decision layer over the *active* (non-superseded) bills for
one or more accounts. It runs two passes and returns supersession pairs; it touches
no DB — the store applies them, and `s2_bill_store.list_active_bills` already hides
superseded rows from the engine.

Pass 1 — exact period. Group by (account, exact billing period); per group keep the
single most authoritative bill and supersede the rest. Authority rank (higher wins;
ties broken by latest bill_id = most recent insert):
  actual read (2) > estimated read (1) > cost-only (0)
So a true-up actual supersedes an earlier estimate; a re-issued actual supersedes a
prior actual (a correction); a stray estimate after an actual is itself superseded.

Pass 2 — coverage. A weak bill (an estimated read, or a full-year documented
estimate) is superseded by the *actual* reads that overlap it **once those actuals
cover ≥ COVERAGE_THRESHOLD of its period**. This is the annual-estimate-vs-monthly-
actuals case: twelve monthly bills replace the floor-area estimate, but a single
month's actual does NOT wipe out the annual estimate (that would drop the other
eleven months). Partial coverage leaves both standing — the same as before Pass 2
existed — so this only ever improves the fully-covered terminal state.

Pure business logic — imports nothing from the platform.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

COVERAGE_THRESHOLD = 0.9  # actuals must cover this fraction of an estimate to supersede it


@dataclass(frozen=True)
class BillKey:
    """The minimum a bill needs to expose for dedup. Ordering-agnostic."""

    bill_id: int
    account_id: int
    period_start: str  # ISO date
    period_end: str  # ISO date
    is_estimated_read: bool
    is_cost_only: bool


def _authority(bill: BillKey) -> int:
    if bill.is_cost_only:
        return 0
    if bill.is_estimated_read:
        return 1
    return 2


def _is_actual(bill: BillKey) -> bool:
    return not bill.is_estimated_read and not bill.is_cost_only


def _is_weak(bill: BillKey) -> bool:
    return bill.is_estimated_read or bill.is_cost_only


def _start(bill: BillKey) -> date:
    return date.fromisoformat(bill.period_start)


def _end(bill: BillKey) -> date:
    return date.fromisoformat(bill.period_end)


def _overlaps(a: BillKey, b: BillKey) -> bool:
    return _start(a) <= _end(b) and _end(a) >= _start(b)


def _coverage_fraction(estimate: BillKey, actuals: list[BillKey]) -> float:
    """Fraction of the estimate's day span covered by the union of the actuals."""
    e_start, e_end = _start(estimate), _end(estimate)
    span_days = (e_end - e_start).days + 1
    if span_days <= 0:
        return 0.0

    # Clip each actual to the estimate window, then union the intervals.
    clipped = sorted(
        (max(_start(a), e_start), min(_end(a), e_end))
        for a in actuals
        if max(_start(a), e_start) <= min(_end(a), e_end)
    )
    if not clipped:
        return 0.0

    covered_days = 0
    cur_start, cur_end = clipped[0]
    for s, t in clipped[1:]:
        if (s - cur_end).days <= 1:  # contiguous or overlapping
            cur_end = max(cur_end, t)
        else:
            covered_days += (cur_end - cur_start).days + 1
            cur_start, cur_end = s, t
    covered_days += (cur_end - cur_start).days + 1
    return covered_days / span_days


def resolve_supersessions(
    bills: list[BillKey], *, coverage_threshold: float = COVERAGE_THRESHOLD
) -> list[tuple[int, int]]:
    """Return (superseded_bill_id, superseding_bill_id) pairs.

    `bills` must be the currently *active* bills (superseded rows already excluded).
    Runs the exact-period pass, then the coverage pass on whatever remains active.
    """
    pairs: list[tuple[int, int]] = []

    # Pass 1 — exact period.
    groups: dict[tuple[int, str, str], list[BillKey]] = {}
    for bill in bills:
        groups.setdefault(
            (bill.account_id, bill.period_start, bill.period_end), []
        ).append(bill)
    for members in groups.values():
        if len(members) < 2:
            continue
        winner = max(members, key=lambda b: (_authority(b), b.bill_id))
        for bill in members:
            if bill.bill_id != winner.bill_id:
                pairs.append((bill.bill_id, winner.bill_id))

    superseded: set[int] = {loser for loser, _ in pairs}

    # Pass 2 — coverage. Only bills still active after Pass 1 participate.
    active = [b for b in bills if b.bill_id not in superseded]
    actuals = [b for b in active if _is_actual(b)]
    for estimate in [b for b in active if _is_weak(b)]:
        covering = [
            a
            for a in actuals
            if a.account_id == estimate.account_id and _overlaps(a, estimate)
        ]
        if not covering:
            continue
        if _coverage_fraction(estimate, covering) >= coverage_threshold:
            winner = max(covering, key=lambda a: (_end(a), a.bill_id))
            pairs.append((estimate.bill_id, winner.bill_id))
            superseded.add(estimate.bill_id)

    return pairs


__all__ = ["BillKey", "COVERAGE_THRESHOLD", "resolve_supersessions"]
