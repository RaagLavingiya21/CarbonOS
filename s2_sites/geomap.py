"""Geography -> emission-factor-region mapping (PRD 5.3).

US site ZIP -> eGRID subregion; non-US country -> IEA country code. MVP stub:
the full ZIP->eGRID crosswalk is seeded alongside the factor library
(scripts/seed_s2_factors.py) in Phase M0. Leaf module — imports nothing internal.
"""

from __future__ import annotations

# TODO(M0): load the full ZIP -> eGRID subregion crosswalk from seeded reference data.
_EGRID_STUB: dict[str, str] = {}


def zip_to_egrid_subregion(zip_code: str) -> str | None:
    """Return the eGRID subregion code for a US ZIP, or None if unmapped."""
    return _EGRID_STUB.get(zip_code.strip()[:5])


def country_to_iea(country_code: str) -> str:
    """Return the IEA country code (ISO-3166 alpha-2 passthrough for now)."""
    return country_code.strip().upper()
