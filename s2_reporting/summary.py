"""Standard Scope 2 summary export (PRD 5.5). MVP stub.

Phase M3 implements the location- vs. market-based summary (factors used,
methodology notes) as PDF/CSV, plus CDP and one buyer-template mapping. Leaf-ish
module — imports only s2_* siblings in later phases.
"""

from __future__ import annotations


def build_summary(*args: object, **kwargs: object) -> dict:
    """Build the standard LB/MB summary payload. Implemented in Phase M3."""
    raise NotImplementedError("s2_reporting.summary.build_summary is a Phase M3 deliverable.")
