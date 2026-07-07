"""Supplier program scorecard (Epic F / P.3.4.c). Pure, DB-free.

Measures how much of the supply base (by count and by emissions) has provided
primary PCF data, the average data quality of those PCFs, and how many suppliers
have their own science-based targets — the metrics that make supplier
engagement's progress legible (and feed the SBTi supplier-engagement target
type in Epic D).
"""

from __future__ import annotations

from s3_suppliers.models import ProgramScorecard, Supplier


def program_scorecard(suppliers: list[Supplier]) -> ProgramScorecard:
    n = len(suppliers)
    if n == 0:
        return ProgramScorecard(0, 0.0, 0.0, None, 0, 0)

    with_pcf = [s for s in suppliers if s.pcf_received]
    total_emissions = sum(s.emissions_kg for s in suppliers)
    covered_emissions = sum(s.emissions_kg for s in with_pcf)
    dqs = [s.dq_score for s in with_pcf if s.dq_score is not None]

    return ProgramScorecard(
        supplier_count=n,
        pcf_coverage_pct=round(len(with_pcf) / n, 4),
        emissions_covered_pct=round(covered_emissions / total_emissions, 4)
        if total_emissions > 0
        else 0.0,
        avg_dq=round(sum(dqs) / len(dqs), 2) if dqs else None,
        sbt_committed_count=sum(1 for s in suppliers if s.supplier_sbt_status == "committed"),
        sbt_validated_count=sum(1 for s in suppliers if s.supplier_sbt_status == "validated"),
    )
