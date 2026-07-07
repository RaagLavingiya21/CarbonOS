"""Scope 1 onboarding — a backend-driven guided setup checklist.

Pure, DB-free. The route feeds it live counts (entities, facilities, sources,
inventories, records, locked inventories) gathered from the org-scoped store;
this module turns those into an ordered checklist that reflects *real* progress
through the Scope 1 setup path — not a hardcoded frontend fiction.
"""

from s1_onboarding.checklist import (
    OnboardingChecklist,
    OnboardingCounts,
    OnboardingStep,
    build_onboarding,
)

__all__ = [
    "OnboardingChecklist",
    "OnboardingCounts",
    "OnboardingStep",
    "build_onboarding",
]
