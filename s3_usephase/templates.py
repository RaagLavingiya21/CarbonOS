"""Sub-sector use-phase templates (Epic H / 11.5).

Pre-built default use profiles + calc mode per consumer sub-sector, so an analyst
can estimate Cat 11 before capturing per-SKU specs. Dated snapshot — tune with
real product/label data. `mode` selects direct vs indirect use-phase.
"""

from __future__ import annotations

from s3_usephase.models import UseProfile

# sub_sector -> (default UseProfile, mode)
_TEMPLATES: dict[str, tuple[UseProfile, str]] = {
    # Appliances/durables: draw power every day over a long life (direct).
    "durables": (UseProfile(uses_per_year=365, lifetime_years=10, sub_sector="durables"), "direct"),
    "appliances": (
        UseProfile(uses_per_year=365, lifetime_years=10, sub_sector="appliances"),
        "direct",
    ),
    # Apparel: emissions come from laundering over the garment's life (indirect).
    "apparel": (UseProfile(uses_per_year=50, lifetime_years=3, sub_sector="apparel"), "indirect"),
    # Beauty/personal care rinse-off: hot water per use (indirect).
    "bpc": (UseProfile(uses_per_year=300, lifetime_years=1, sub_sector="bpc"), "indirect"),
    # Consumer electronics: active + standby power (direct).
    "electronics": (
        UseProfile(uses_per_year=300, lifetime_years=4, sub_sector="electronics"),
        "direct",
    ),
}


def available_sub_sectors() -> list[str]:
    return sorted(_TEMPLATES)


def get_template(sub_sector: str) -> tuple[UseProfile, str]:
    """Return (default UseProfile, mode) for a sub-sector.

    Raises KeyError for an unknown sub-sector.
    """
    key = (sub_sector or "").strip().lower()
    if key not in _TEMPLATES:
        raise KeyError(f"Unknown sub-sector '{sub_sector}' (have {available_sub_sectors()}).")
    profile, mode = _TEMPLATES[key]
    # Return a fresh copy so callers can safely mutate.
    return (
        UseProfile(profile.uses_per_year, profile.lifetime_years, profile.sub_sector),
        mode,
    )
