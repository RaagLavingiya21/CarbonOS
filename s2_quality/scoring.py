"""Data-completeness / coverage scoring (PRD 5.6).

Scores how much of a portfolio's consumption is backed by real metered data vs.
documented estimates, and flags sites with no data at all — the "report-ready"
indicator. Pure business logic: it operates on plain bill dicts (from s2_bill_store)
and a list of active site ids; imports nothing internal.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

# Data-source ranking, best first (PRD 5.2 acceptance). MVP distinguishes metered
# actuals from documented estimates; landlord/benchmark sources slot in once those
# data paths persist bills.
DATA_SOURCE_RANK = ("actual", "landlord_provided", "benchmark_proxy", "documented_estimate")


def classify_source(bill: dict) -> str:
    """Classify a bill's data source for coverage scoring."""
    if bill.get("is_estimated_read") or bill.get("ingestion_method") == "estimate":
        return "documented_estimate"
    return "actual"


@dataclass(frozen=True)
class SiteCoverage:
    site_id: int
    total_mwh: float
    actual_mwh: float
    estimate_mwh: float
    coverage_fraction: float  # actual / total (0 when a site has no data)
    has_data: bool


@dataclass(frozen=True)
class PortfolioCoverage:
    total_mwh: float
    actual_mwh: float
    estimate_mwh: float
    coverage_fraction: float  # share of consumption that is actual (0..1)
    estimation_fraction: float  # share that is documented estimate (0..1)
    site_count: int
    sites_with_data: int
    sites_missing_data: int
    per_site: list[SiteCoverage] = field(default_factory=list)


def compute_coverage(bills: list[dict], site_ids: list[int]) -> PortfolioCoverage:
    """Compute per-site + portfolio coverage from active bills and the site list."""
    actual_by_site: dict[int, float] = defaultdict(float)
    estimate_by_site: dict[int, float] = defaultdict(float)

    for bill in bills:
        mwh = bill.get("canonical_mwh")
        if mwh is None:
            continue  # cost-only rows carry no consumption
        site_id = int(bill["site_id"])
        if classify_source(bill) == "documented_estimate":
            estimate_by_site[site_id] += float(mwh)
        else:
            actual_by_site[site_id] += float(mwh)

    per_site: list[SiteCoverage] = []
    for site_id in site_ids:
        actual = actual_by_site.get(site_id, 0.0)
        estimate = estimate_by_site.get(site_id, 0.0)
        total = actual + estimate
        per_site.append(
            SiteCoverage(
                site_id=site_id,
                total_mwh=total,
                actual_mwh=actual,
                estimate_mwh=estimate,
                coverage_fraction=(actual / total) if total > 0 else 0.0,
                has_data=total > 0,
            )
        )

    total_actual = sum(s.actual_mwh for s in per_site)
    total_estimate = sum(s.estimate_mwh for s in per_site)
    total_mwh = total_actual + total_estimate
    return PortfolioCoverage(
        total_mwh=total_mwh,
        actual_mwh=total_actual,
        estimate_mwh=total_estimate,
        coverage_fraction=(total_actual / total_mwh) if total_mwh > 0 else 0.0,
        estimation_fraction=(total_estimate / total_mwh) if total_mwh > 0 else 0.0,
        site_count=len(site_ids),
        sites_with_data=sum(1 for s in per_site if s.has_data),
        sites_missing_data=sum(1 for s in per_site if not s.has_data),
        per_site=per_site,
    )
