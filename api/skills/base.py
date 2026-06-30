"""Base class for platform chat agent skills."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Skill(ABC):
    """Encapsulates a group of related agent capabilities behind one tool."""

    name: str
    description: str
    parameters_schema: dict[str, Any]

    @abstractmethod
    async def run(self, action: str, **kwargs: Any) -> dict[str, Any]:
        """Execute an action and return a structured result dict."""
