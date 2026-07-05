"""Pydantic request/response models for the Scope 2 ("Grid") API layer.

Kept separate from api/models/schemas.py so the Scope 2 module shares no domain
types with the Carbon OS (Scope 3 / PACT) product. Only infra types (auth, health)
are shared at the app level.
"""

from __future__ import annotations

from pydantic import BaseModel

from s2_sites.templates import SITE_TEMPLATES, SiteTemplate


class Scope2HealthResponse(BaseModel):
    status: str
    module: str = "scope2"


class SiteTemplateDTO(BaseModel):
    site_type: str
    label: str
    energy_carriers: list[str]
    default_ownership: str
    default_lease_type: str
    notes: str
    typical_utilities: list[str]

    @classmethod
    def from_domain(cls, template: SiteTemplate) -> "SiteTemplateDTO":
        return cls(
            site_type=template.site_type,
            label=template.label,
            energy_carriers=list(template.energy_carriers),
            default_ownership=template.default_ownership,
            default_lease_type=template.default_lease_type,
            notes=template.notes,
            typical_utilities=list(template.typical_utilities),
        )


def all_site_template_dtos() -> list[SiteTemplateDTO]:
    return [SiteTemplateDTO.from_domain(t) for t in SITE_TEMPLATES.values()]
