"""Multi-regime Scope 1 disclosure exports (ESRS E1, CDP, EPA GHGRP, SB 253).

Pipeline: DisclosureData + DisclosureMeta --(regime mapper)--> neutral Disclosure
IR --(render_pdf / render_xlsx)--> bytes. Adding a regime = one mapper.
"""

from s1_reporting.disclosures.ir import Disclosure, Section
from s1_reporting.disclosures.mappers import (
    REGIME_MAPPERS,
    map_cdp,
    map_esrs_e1,
    map_ghgrp,
    map_sb253,
)
from s1_reporting.disclosures.render import render_pdf, render_xlsx

__all__ = [
    "REGIME_MAPPERS",
    "Disclosure",
    "Section",
    "map_cdp",
    "map_esrs_e1",
    "map_ghgrp",
    "map_sb253",
    "render_pdf",
    "render_xlsx",
]
