"""Pure onboarding-checklist logic for the Scope 1 guided setup wizard.

`build_onboarding(counts)` maps a snapshot of the org's Scope 1 objects to an
ordered list of setup steps, each marked done/not-done, plus overall progress
and the key of the next incomplete step. Framework- and DB-free so it can be
unit-tested without HTTP or Supabase.

The step order mirrors the real dependency chain of the setup flow:
entity -> facility -> combustion source (boundary) -> inventory -> activity
data -> lock & disclose.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class OnboardingCounts:
    """Live counts gathered from the org-scoped store (all default 0)."""

    entities: int = 0
    facilities: int = 0
    sources: int = 0  # in-scope (non-excluded) emission sources
    inventories: int = 0
    records: int = 0  # activity records across all inventories
    locked_inventories: int = 0


@dataclass(frozen=True)
class OnboardingStep:
    key: str
    title: str
    description: str
    href: str
    cta: str
    done: bool
    count: int


@dataclass(frozen=True)
class OnboardingChecklist:
    steps: list[OnboardingStep] = field(default_factory=list)
    complete: int = 0
    total: int = 0
    pct: float = 0.0
    next_key: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.total > 0 and self.complete == self.total


# Static step definitions. `count` extracts the number shown as the step's
# progress detail; the step is "done" once that count is > 0.
@dataclass(frozen=True)
class _StepDef:
    key: str
    title: str
    description: str
    href: str
    cta: str
    count: Callable[[OnboardingCounts], int]


_STEPS: tuple[_StepDef, ...] = (
    _StepDef(
        key="entity",
        title="Create your reporting entity",
        description="Add the legal entity you're reporting for and its consolidation approach.",
        href="/scope-1/setup",
        cta="Add entity",
        count=lambda c: c.entities,
    ),
    _StepDef(
        key="facility",
        title="Add a facility",
        description="Register a site or location where fuel is combusted or fleet is based.",
        href="/scope-1/setup",
        cta="Add facility",
        count=lambda c: c.facilities,
    ),
    _StepDef(
        key="source",
        title="Define combustion sources",
        description="Set your inventory boundary: the stationary and mobile sources in scope.",
        href="/scope-1/setup",
        cta="Add sources",
        count=lambda c: c.sources,
    ),
    _StepDef(
        key="inventory",
        title="Open a reporting-year inventory",
        description="Create the reporting period you'll collect activity data against.",
        href="/scope-1/setup",
        cta="Create inventory",
        count=lambda c: c.inventories,
    ),
    _StepDef(
        key="data",
        title="Enter activity data",
        description="Add fuel and fleet consumption with evidence — manual, CSV, or a scanned bill.",
        href="/scope-1/data",
        cta="Add data",
        count=lambda c: c.records,
    ),
    _StepDef(
        key="disclose",
        title="Lock & disclose",
        description="Review per-gas totals, lock the inventory, and export your SB 253 disclosure.",
        href="/scope-1/report",
        cta="Review report",
        count=lambda c: c.locked_inventories,
    ),
)


def build_onboarding(counts: OnboardingCounts) -> OnboardingChecklist:
    """Turn a counts snapshot into an ordered, progress-tracked checklist."""
    steps: list[OnboardingStep] = []
    for defn in _STEPS:
        n = defn.count(counts)
        steps.append(
            OnboardingStep(
                key=defn.key,
                title=defn.title,
                description=defn.description,
                href=defn.href,
                cta=defn.cta,
                done=n > 0,
                count=n,
            )
        )

    complete = sum(1 for s in steps if s.done)
    total = len(steps)
    next_key = next((s.key for s in steps if not s.done), None)
    pct = (complete / total * 100.0) if total else 0.0
    return OnboardingChecklist(
        steps=steps,
        complete=complete,
        total=total,
        pct=pct,
        next_key=next_key,
    )
