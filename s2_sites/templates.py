"""Prebuilt consumer-sector site templates (PRD 5.3).

Each template preconfigures the likely energy carriers, typical utility setup,
and the default landlord/tenant boundary per the GHG Protocol, so creating a site
takes minutes instead of the multi-hour manual boundary configuration incumbents
require. Leaf module — imports nothing internal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Site-type identifiers (kept in sync with the s2_sites.site_type DB enum).
SITE_TYPES = (
    "retail",
    "grocery",
    "food_service",
    "manufacturing",
    "warehouse_dc",
    "office",
)


@dataclass(frozen=True)
class SiteTemplate:
    site_type: str
    label: str
    energy_carriers: tuple[str, ...]
    default_ownership: str  # owned | tenant_metered | landlord_metered | sub_metered
    default_lease_type: str  # gross | nnn | modified | owned
    notes: str = ""
    typical_utilities: tuple[str, ...] = field(default_factory=tuple)


SITE_TEMPLATES: dict[str, SiteTemplate] = {
    "retail": SiteTemplate(
        site_type="retail",
        label="Retail store",
        energy_carriers=("electricity",),
        default_ownership="landlord_metered",
        default_lease_type="nnn",
        notes="Mall/strip retail is usually landlord-metered; expect the leased-site workflow.",
        typical_utilities=("electric",),
    ),
    "grocery": SiteTemplate(
        site_type="grocery",
        label="Grocery",
        energy_carriers=("electricity", "natural_gas"),
        default_ownership="tenant_metered",
        default_lease_type="nnn",
        notes="High refrigeration load; often tenant-metered electricity plus gas.",
        typical_utilities=("electric", "gas"),
    ),
    "food_service": SiteTemplate(
        site_type="food_service",
        label="Restaurant / food service",
        energy_carriers=("electricity", "natural_gas"),
        default_ownership="tenant_metered",
        default_lease_type="modified",
        typical_utilities=("electric", "gas"),
    ),
    "manufacturing": SiteTemplate(
        site_type="manufacturing",
        label="CPG / manufacturing plant",
        energy_carriers=("electricity", "natural_gas", "steam"),
        default_ownership="owned",
        default_lease_type="owned",
        typical_utilities=("electric", "gas", "steam"),
    ),
    "warehouse_dc": SiteTemplate(
        site_type="warehouse_dc",
        label="Apparel DC / warehouse",
        energy_carriers=("electricity",),
        default_ownership="tenant_metered",
        default_lease_type="nnn",
        typical_utilities=("electric",),
    ),
    "office": SiteTemplate(
        site_type="office",
        label="Service / office",
        energy_carriers=("electricity",),
        default_ownership="landlord_metered",
        default_lease_type="gross",
        notes="Gross-lease offices frequently have no tenant meter; expect estimation/benchmark.",
        typical_utilities=("electric",),
    ),
}


def get_template(site_type: str) -> SiteTemplate:
    """Return the template for a site type, raising a clear error if unknown."""
    key = site_type.strip().lower()
    if key not in SITE_TEMPLATES:
        raise KeyError(f"Unknown site_type '{site_type}'. Known: {SITE_TYPES}.")
    return SITE_TEMPLATES[key]
