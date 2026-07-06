"""Geography -> emission-factor-region mapping (PRD 5.3).

US sites map to an EPA eGRID subregion (the correct grid-average region for
location-based Scope 2); non-US sites map to an IEA country. The 26 eGRID
subregion CODES below are the standard EPA identifiers — labels only, not emission
values (those live in s2_factor_library, seeded with citations).

A ZIP -> subregion crosswalk can be injected once the EPA Power Profiler table is
loaded; until then a site's subregion is set explicitly on the site (validated
against this list). Leaf module — imports nothing internal.
"""

from __future__ import annotations

# EPA eGRID subregion code -> human-readable name (for the site-create dropdown).
EGRID_SUBREGIONS: dict[str, str] = {
    "AKGD": "ASCC Alaska Grid",
    "AKMS": "ASCC Miscellaneous",
    "AZNM": "WECC Southwest",
    "CAMX": "WECC California",
    "ERCT": "ERCOT All",
    "FRCC": "FRCC All",
    "HIMS": "HICC Miscellaneous",
    "HIOA": "HICC Oahu",
    "MROE": "MRO East",
    "MROW": "MRO West",
    "NEWE": "NPCC New England",
    "NWPP": "WECC Northwest",
    "NYCW": "NPCC NYC/Westchester",
    "NYLI": "NPCC Long Island",
    "NYUP": "NPCC Upstate NY",
    "RFCE": "RFC East",
    "RFCM": "RFC Michigan",
    "RFCW": "RFC West",
    "RMPA": "WECC Rockies",
    "SPNO": "SPP North",
    "SPSO": "SPP South",
    "SRMV": "SERC Mississippi Valley",
    "SRMW": "SERC Midwest",
    "SRSO": "SERC South",
    "SRTV": "SERC Tennessee Valley",
    "SRVC": "SERC Virginia/Carolina",
}

# ZIP -> eGRID subregion crosswalk (seed from EPA Power Profiler when available).
_ZIP_TO_EGRID: dict[str, str] = {}


def is_valid_subregion(code: str) -> bool:
    """Whether `code` is a recognized eGRID subregion."""
    return code.strip().upper() in EGRID_SUBREGIONS


def zip_to_egrid_subregion(zip_code: str) -> str | None:
    """Return the eGRID subregion for a US ZIP, or None if not in the crosswalk."""
    return _ZIP_TO_EGRID.get(zip_code.strip()[:5])


def country_to_iea(country_code: str) -> str:
    """Return the IEA country code (ISO-3166 alpha-2 passthrough for now)."""
    return country_code.strip().upper()
