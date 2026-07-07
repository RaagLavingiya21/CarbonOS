"""Estimated-read / true-up de-duplication (PRD 5.6 immutability).

Utilities issue an *estimated* meter read for a period, then a later bill *trues it
up* with the actual read for the same period. A cost-only row is a weaker signal
still. Without dedup the estimate and its true-up both feed the calc engine and the
period's consumption is double-counted.

This module is the pure decision layer: given the *active* (non-superseded) bills
for one or more accounts, it groups them by (account, exact billing period) and, per
group, keeps the single most authoritative bill and marks every other as superseded
by it. It touches no DB — the store applies the returned supersession pairs, and
`s2_bill_store.list_active_bills` already hides superseded rows from the engine.

Authority rank (higher wins; ties broken by latest bill_id = most recent insert):
  actual read (2) > estimated read (1) > cost-only (0)

So: a true-up actual supersedes an earlier estimate; a re-issued actual supersedes
the prior actual (a correction); a stray estimate arriving after an actual is itself
superseded by the standing actual — never the other way round.

Scope note: matching is on the *exact* (period_start, period_end). Reconciling a
full-year documented estimate against overlapping monthly actuals is a different,
overlap-based problem and is intentionally deferred (see SCOPE2_STATUS.md §6).

Pure business logic — imports nothing from the platform.
"""

from __future__ import annotations

from dataclasses import dataclass


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


def resolve_supersessions(bills: list[BillKey]) -> list[tuple[int, int]]:
    """Return (superseded_bill_id, superseding_bill_id) pairs.

    `bills` must be the currently *active* bills (superseded rows already excluded).
    Within each (account, period) group the winner is the highest-authority bill,
    ties broken by the larger bill_id (latest insert). Every other bill in the group
    is reported as superseded by that winner. Groups of one produce nothing.
    """
    groups: dict[tuple[int, str, str], list[BillKey]] = {}
    for bill in bills:
        groups.setdefault(
            (bill.account_id, bill.period_start, bill.period_end), []
        ).append(bill)

    pairs: list[tuple[int, int]] = []
    for members in groups.values():
        if len(members) < 2:
            continue
        winner = max(members, key=lambda b: (_authority(b), b.bill_id))
        for bill in members:
            if bill.bill_id != winner.bill_id:
                pairs.append((bill.bill_id, winner.bill_id))
    return pairs


__all__ = ["BillKey", "resolve_supersessions"]
