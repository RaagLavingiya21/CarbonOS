"""SBTi readiness: Category A/B + version-aware Scope 3 coverage math (Epic C /
unit P.1.3; reused by Epic D's target wizard).

Pure function: takes an ObligationProfile and a {scope3_category: kg_co2e} dict
(supplied by the Epic A corporate inventory later — DB-free here). Computes:
  - Category A/B classification (A => Scope 3 targets mandatory + base-year
    limited assurance), three-valued when the deciding facts are unknown.
  - V2.0 coverage: EVERY Scope 3 category that is >=5% of total Scope 3 must be
    covered by a target (per-category, not an aggregate quota).
  - V1.x coverage: aggregate >=67% (near-term) / >=90% (net-zero).

Honesty (per research/reg-status-verified.md): the V2.0 NET-ZERO coverage % is
NOT cleanly confirmed, so it is NEVER hardcoded — net-zero readiness under V2.0
returns meets_requirement=None with a "verify" note.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from s3_obligations.models import ObligationProfile

_CAT_A_REVENUE_USD = 1_000_000_000
_CAT_A_EMPLOYEES = 500
_V2_CATEGORY_THRESHOLD = 0.05  # every category >=5% of Scope 3 needs a target
_V1_NEAR_TERM_COVERAGE = 0.67
_V1_NET_ZERO_COVERAGE = 0.90


@dataclass
class CategoryCoverage:
    scope3_category: int
    kg_co2e: float
    pct_of_scope3: float
    requires_coverage: bool  # V2.0: pct >= 5%
    is_covered: bool  # has a target


@dataclass
class SBTiReadiness:
    category_class: str  # "A" | "B" | "uncertain"
    scope3_target_mandatory: bool
    base_year_assurance_required: bool
    version: str  # "v2.0" | "v1.3.1"
    horizon: str  # "near_term" | "net_zero"
    total_scope3_kg: float
    category_coverage: list[CategoryCoverage] = field(default_factory=list)
    required_categories: list[int] = field(default_factory=list)
    covered_categories: list[int] = field(default_factory=list)
    coverage_gap: list[int] = field(default_factory=list)  # required but not covered
    meets_requirement: bool | None = None  # None = undetermined / unconfirmed
    notes: list[str] = field(default_factory=list)


def classify_category(profile: ObligationProfile) -> str:
    """Category A if revenue >$1B OR >500 employees (high-income assumed), else
    B; 'uncertain' when neither deciding fact is known and A is not yet met."""
    rev_a = (
        None
        if profile.annual_revenue_usd is None
        else (profile.annual_revenue_usd > _CAT_A_REVENUE_USD)
    )
    emp_a = None if profile.employee_count is None else (profile.employee_count > _CAT_A_EMPLOYEES)
    if rev_a is True or emp_a is True:
        return "A"
    if rev_a is False and emp_a is False:
        return "B"
    return "uncertain"


def assess_sbti_readiness(
    profile: ObligationProfile,
    scope3_by_category: dict[int, float],
    *,
    covered_categories: set[int] | None = None,
    version: str = "v2.0",
    horizon: str = "near_term",
) -> SBTiReadiness:
    """Assess SBTi Scope 3 coverage readiness for a profile + inventory."""
    covered = set(covered_categories or set())
    category_class = classify_category(profile)
    is_a = category_class == "A"
    total = sum(v for v in scope3_by_category.values() if v and v > 0)

    readiness = SBTiReadiness(
        category_class=category_class,
        scope3_target_mandatory=is_a,
        base_year_assurance_required=is_a,
        version=version,
        horizon=horizon,
        total_scope3_kg=total,
        covered_categories=sorted(covered),
    )

    if category_class == "uncertain":
        readiness.notes.append(
            "Cannot classify Category A/B — provide revenue and/or employee count."
        )
    if is_a:
        readiness.notes.append(
            "Category A: Scope 3 targets are mandatory and base-year limited assurance is required."
        )

    if total <= 0:
        readiness.notes.append("No Scope 3 inventory provided — coverage cannot be computed.")
        readiness.meets_requirement = None
        return readiness

    coverage = [
        CategoryCoverage(
            scope3_category=cat,
            kg_co2e=kg,
            pct_of_scope3=kg / total,
            requires_coverage=(kg / total) >= _V2_CATEGORY_THRESHOLD,
            is_covered=cat in covered,
        )
        for cat, kg in sorted(scope3_by_category.items())
        if kg and kg > 0
    ]
    readiness.category_coverage = coverage

    if version.startswith("v2"):
        _assess_v2(readiness, coverage, covered, horizon)
    else:
        _assess_v1(readiness, coverage, covered, total, horizon)

    return readiness


def _assess_v2(
    readiness: SBTiReadiness,
    coverage: list[CategoryCoverage],
    covered: set[int],
    horizon: str,
) -> None:
    """V2.0: every category >=5% of Scope 3 needs a target (per-category)."""
    required = [c.scope3_category for c in coverage if c.requires_coverage]
    readiness.required_categories = required
    gap = [cat for cat in required if cat not in covered]
    readiness.coverage_gap = gap

    if horizon == "net_zero":
        # V2.0 net-zero coverage % is NOT cleanly confirmed — do not assert.
        readiness.meets_requirement = None
        readiness.notes.append(
            "V2.0 net-zero coverage % is unconfirmed — verify against the V2.0 standard "
            "text before asserting long-term readiness (near-total expected)."
        )
    else:
        readiness.meets_requirement = len(gap) == 0
        if gap:
            readiness.notes.append(
                f"Near-term V2.0: categories {gap} are >=5% of Scope 3 but have no target."
            )


def _assess_v1(
    readiness: SBTiReadiness,
    coverage: list[CategoryCoverage],
    covered: set[int],
    total: float,
    horizon: str,
) -> None:
    """V1.x: aggregate coverage >=67% near-term / >=90% net-zero."""
    threshold = _V1_NET_ZERO_COVERAGE if horizon == "net_zero" else _V1_NEAR_TERM_COVERAGE
    covered_pct = sum(c.pct_of_scope3 for c in coverage if c.scope3_category in covered)
    readiness.required_categories = [c.scope3_category for c in coverage]
    readiness.meets_requirement = covered_pct >= threshold
    readiness.notes.append(
        f"V1.x {horizon}: covered {covered_pct:.0%} of Scope 3 (need >={threshold:.0%})."
    )
