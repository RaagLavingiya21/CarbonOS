"""Dataclasses for the obligation engine (Epic C).

`ObligationProfile` is a DB-free input (the API layer maps the persisted
`company_profiles` row onto it). `Obligation` is one evaluated result.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ObligationProfile:
    """The company facts the ruleset predicates read. Unknown fields are None/
    empty, which the engine surfaces as `uncertain` rather than a false 'no'."""

    annual_revenue_usd: float | None = None
    employee_count: int | None = None
    is_us_entity: bool = False
    does_business_in_ca: bool = False
    eu_turnover_eur: float | None = None
    eu_subsidiary: bool = False
    eu_branch_turnover_eur: float | None = None
    listed_jurisdictions: list[str] = field(default_factory=list)
    sector: str = ""
    is_flag_sector: bool = False
    key_customers: list[str] = field(default_factory=list)


@dataclass
class DueItem:
    what: str
    date: str | None  # ISO date, or None for ad-hoc/contract-linked
    note: str | None = None


@dataclass
class Obligation:
    """One evaluated obligation for a profile."""

    rule_id: str
    framework: str
    applies: str  # "yes" | "uncertain" | "no"
    reason: str  # why it triggered (or why uncertain)
    threshold_detail: str
    confidence: str  # "confirmed" | "partial"
    status: str  # "in_force" | "watch"
    due: list[DueItem] = field(default_factory=list)
    assurance: str | None = None
    citation: str = ""
    priority: int = 0
    ruleset_version: str = ""


@dataclass
class EvaluationResult:
    """Full engine output for a profile."""

    ruleset_version: str
    applicable: list[Obligation] = field(default_factory=list)  # applies == "yes"
    uncertain: list[Obligation] = field(default_factory=list)  # applies == "uncertain"
    not_applicable: list[Obligation] = field(default_factory=list)  # applies == "no"

    @property
    def timeline(self) -> list[tuple[str, str, str]]:
        """Flatten dated due-items from applicable + uncertain obligations,
        sorted by date. Returns (date, framework, what)."""
        items: list[tuple[str, str, str]] = []
        for obligation in self.applicable + self.uncertain:
            for due in obligation.due:
                if due.date:
                    items.append((due.date, obligation.framework, due.what))
        return sorted(items, key=lambda t: t[0])
