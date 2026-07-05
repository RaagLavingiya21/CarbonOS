"""Coverage / data-quality scoring (PRD 5.6). MVP stub.

Phase M2 implements the portfolio coverage score: the share of consumption backed
by actual/landlord/benchmark data vs. pure estimate, plus an estimation-coverage
percentage. Leaf-ish module — imports only s2_* siblings in later phases.
"""

from __future__ import annotations

# Data-source ranking, best first (PRD 5.2 acceptance).
DATA_SOURCE_RANK = ("actual", "landlord_provided", "benchmark_proxy", "documented_estimate")


def coverage_score(*args: object, **kwargs: object) -> float:
    """Return a 0-1 portfolio coverage score. Implemented in Phase M2."""
    raise NotImplementedError("s2_quality.scoring.coverage_score is a Phase M2 deliverable.")
