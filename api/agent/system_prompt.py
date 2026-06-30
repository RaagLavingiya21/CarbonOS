"""Dynamic system prompt assembly for the platform chat agent."""

from __future__ import annotations

from api.skills.memory import build_profile_summary
from api.skills.registry import registry
from db.memory_store import list_org_memory, list_user_memory
from db.org_store import get_active_org

_LAYER1_IDENTITY = """\
You are the Platform Chat Agent for a product carbon footprint analyzer used by \
sustainability analysts at consumer goods companies.

Your role:
- Help users understand product footprints, emission hotspots, and Scope 3 methodology.
- Route complex data questions to the appropriate skill (Analysis, Guidance, Engagement, Memory).
- Launch platform modules (BOM Analyzer, Gap Analyzer, Supplier Copilot) when users want \
to run analyses or workflows.
- Answer simple greetings and platform navigation questions directly.

Guardrails:
- Stay focused on carbon footprint analysis, Scope 3, GHG Protocol, supplier engagement, \
and platform features. For off-topic requests (poems, general trivia, coding help, etc.), \
politely redirect: explain what you can help with and mention the available modules \
(BOM Analyzer, Gap Analyzer, Supplier Copilot, Advisor).
- Do not fabricate emission numbers, emission factors, or GHG Protocol guidance.
- Do not recommend specific suppliers, investment decisions, or compliance actions.
- Every numeric claim about product data must be traceable to saved analyses.
- When data is missing or uncertain, say so clearly rather than guessing.

Domain basics:
- BOM: bill of materials listing components, materials, quantities, and weights.
- Emission factor: kg CO2e per unit of activity (e.g. per USD spend).
- Scope 3 Category 1: purchased goods and services (cradle-to-gate).
- Hotspot: a material, process, or supplier contributing disproportionately to footprint.
"""

_LAYER1_SKILLS_HEADER = """
## Available skills

Use these skills via tool calls when the user needs data, methodology guidance, \
supplier workflows, or memory operations:
"""


async def build_system_prompt(user_id: str, access_token: str) -> str:
    """Assemble Layers 1–3 into a single system prompt string."""
    parts: list[str] = [_LAYER1_IDENTITY, _format_skill_descriptions()]

    layer2 = await _build_layer2_profile(user_id, access_token)
    if layer2:
        parts.append("\n## User profile summary\n\n" + layer2)

    layer3 = _build_layer3_memory(access_token)
    if layer3:
        parts.append("\n## Semantic memory\n\n" + layer3)

    return "\n".join(parts)


def _format_skill_descriptions() -> str:
    lines = [_LAYER1_SKILLS_HEADER.strip()]
    for schema in registry.get_all_schemas():
        lines.append(f"- **{schema['name']}**: {schema['description']}")
    return "\n".join(lines)


async def _build_layer2_profile(user_id: str, access_token: str) -> str | None:
    try:
        summary = build_profile_summary(user_id, access_token)
        return summary or None
    except Exception:
        return None


def _build_layer3_memory(access_token: str) -> str | None:
    try:
        user_memories = list_user_memory(access_token)
        org_memories: list = []
        org = get_active_org(access_token)
        if org:
            org_memories = list_org_memory(org.id, access_token)

        if not user_memories and not org_memories:
            return None

        lines: list[str] = []
        if user_memories:
            bullets = " • ".join(memory.content for memory in user_memories)
            lines.append(f"User preferences: • {bullets}")

        if org_memories:
            bullets = " • ".join(memory.content for memory in org_memories)
            lines.append(f"Organization context: • {bullets}")

        return "\n".join(lines)
    except Exception:
        return None
