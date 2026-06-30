"""Registry of platform chat agent skills."""

from __future__ import annotations

from typing import Any

from api.skills.analysis import analysis_skill
from api.skills.base import Skill
from api.skills.engagement import engagement_skill
from api.skills.guidance import guidance_skill
from api.skills.memory import memory_skill


class SkillRegistry:
    """Maps skill names to skill instances and exposes schemas for the agent."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {
            analysis_skill.name: analysis_skill,
            guidance_skill.name: guidance_skill,
            engagement_skill.name: engagement_skill,
            memory_skill.name: memory_skill,
        }

    def get_skill(self, name: str) -> Skill | None:
        """Return a skill by name, or None if not registered."""
        return self._skills.get(name)

    def list_skills(self) -> list[Skill]:
        """Return all registered skills."""
        return list(self._skills.values())

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """Return Anthropic-tool-style schemas for all registered skills."""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "input_schema": skill.parameters_schema,
            }
            for skill in self._skills.values()
        ]

    def __contains__(self, name: str) -> bool:
        return name in self._skills


registry = SkillRegistry()
