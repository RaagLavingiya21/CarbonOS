"""Scope 1 consolidation — the GHG Protocol multiplier logic.

Pure, DB-free. Computes the [0.0-1.0] consolidation multiplier for an entity
under a chosen approach (equity share / financial control / operational control),
per research/2.2 section A2. The approach is inventory-level and immutable.
"""

from s1_consolidation.multiplier import (
    ConsolidationResult,
    compute_consolidation_multiplier,
)

__all__ = ["ConsolidationResult", "compute_consolidation_multiplier"]
