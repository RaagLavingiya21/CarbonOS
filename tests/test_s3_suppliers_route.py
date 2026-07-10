"""DB-free tests for the Epic F supplier route helper: build Supplier objects
from stored rows and run cohorting + scorecard end-to-end."""

from __future__ import annotations

from api.routes.scope3_suppliers import supplier_from_row
from s3_suppliers.cohorting import build_cohort
from s3_suppliers.scorecard import program_scorecard

_ROWS = [
    {
        "supplier_id": 1,
        "name": "BigCotton",
        "scope3_category": 1,
        "emissions_kg": 5000,
        "spend_usd": 100000,
        "pcf_received": True,
        "dq_score": 80,
        "supplier_sbt_status": "committed",
    },
    {
        "supplier_id": 2,
        "name": "SmallDye",
        "scope3_category": 1,
        "emissions_kg": 500,
        "spend_usd": 20000,
        "pcf_received": False,
        "dq_score": None,
        "supplier_sbt_status": "none",
    },
    {
        "supplier_id": 3,
        "name": "Freighter",
        "scope3_category": 4,
        "emissions_kg": 2000,
        "spend_usd": 50000,
        "pcf_received": True,
        "dq_score": 60,
        "supplier_sbt_status": "validated",
    },
]


def test_supplier_from_row():
    s = supplier_from_row(_ROWS[0])
    assert s.supplier_id == "1" and s.scope3_category == 1 and s.pcf_received is True


def test_cohort_from_rows():
    suppliers = [supplier_from_row(r) for r in _ROWS]
    cohort = build_cohort(suppliers, {1}, top_n=1)
    assert cohort.members[0].supplier_id == "1"
    assert abs(cohort.emissions_covered_pct - 5000 / 5500) < 1e-4


def test_scorecard_from_rows():
    sc = program_scorecard([supplier_from_row(r) for r in _ROWS])
    assert sc.supplier_count == 3
    assert sc.avg_dq == 70.0  # mean of 80, 60
    assert sc.sbt_committed_count == 1 and sc.sbt_validated_count == 1
