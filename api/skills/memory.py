"""Memory skill — user/org semantic memory and profile summaries."""

from __future__ import annotations

from typing import Any

from api.skills.base import Skill
from db.copilot_store import get_all_engagements
from db.memory_store import (
    OrgMemory,
    UserMemory,
    create_org_memory,
    create_user_memory,
    list_org_memory,
    list_user_memory,
)
from db.org_store import get_user_org, list_members
from db.reader import get_all_products

_ACTIVE_ENGAGEMENT_STATUSES = {"open", "drafted", "sent", "awaiting_response"}


class MemorySkill(Skill):
    name = "memory"
    description = (
        "Read and write user and org semantic memory, and build a lightweight "
        "profile summary for agent context."
    )
    parameters_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "read_user_memory",
                    "write_user_memory",
                    "read_org_memory",
                    "write_org_memory",
                    "build_profile_summary",
                ],
                "description": "The memory operation to perform.",
            },
            "access_token": {
                "type": "string",
                "description": "Supabase access token for the authenticated user.",
            },
            "user_id": {
                "type": "string",
                "description": "User ID (required for write_user_memory).",
            },
            "content": {
                "type": "string",
                "description": "Memory content to store.",
            },
            "category": {
                "type": "string",
                "description": (
                    "Memory category (e.g. preference, focus_area, company_context, target)."
                ),
            },
            "org_id": {
                "type": "string",
                "description": "Organization ID (required for org memory actions).",
            },
            "created_by": {
                "type": "string",
                "description": "User ID of the org memory author (for write_org_memory).",
            },
        },
        "required": ["action", "access_token"],
    }

    async def run(self, action: str, **kwargs: Any) -> dict[str, Any]:
        handlers = {
            "read_user_memory": self._read_user_memory,
            "write_user_memory": self._write_user_memory,
            "read_org_memory": self._read_org_memory,
            "write_org_memory": self._write_org_memory,
            "build_profile_summary": self._build_profile_summary,
        }
        handler = handlers.get(action)
        if handler is None:
            return _error(action, f"Unknown action: {action}")
        try:
            return handler(**kwargs)
        except Exception as exc:
            return _error(action, str(exc))

    def _read_user_memory(self, *, access_token: str, **_: Any) -> dict[str, Any]:
        memories = list_user_memory(access_token)
        return _success(
            "read_user_memory",
            {
                "count": len(memories),
                "memories": [_user_memory_dict(m) for m in memories],
            },
        )

    def _write_user_memory(
        self,
        *,
        access_token: str,
        user_id: str | None = None,
        content: str | None = None,
        category: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        if not user_id:
            return _error("write_user_memory", "Provide user_id.")
        if not content or not content.strip():
            return _error("write_user_memory", "Provide content.")
        if not category or not category.strip():
            return _error("write_user_memory", "Provide category.")

        memory_id = create_user_memory(
            content.strip(),
            category.strip(),
            user_id=user_id,
            access_token=access_token,
        )
        return _success("write_user_memory", {"memory_id": memory_id})

    def _read_org_memory(
        self,
        *,
        access_token: str,
        org_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        if not org_id:
            return _error("read_org_memory", "Provide org_id.")

        memories = list_org_memory(org_id, access_token)
        return _success(
            "read_org_memory",
            {
                "org_id": org_id,
                "count": len(memories),
                "memories": [_org_memory_dict(m) for m in memories],
            },
        )

    def _write_org_memory(
        self,
        *,
        access_token: str,
        org_id: str | None = None,
        content: str | None = None,
        category: str | None = None,
        created_by: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        if not org_id:
            return _error("write_org_memory", "Provide org_id.")
        if not created_by:
            return _error("write_org_memory", "Provide created_by.")
        if not content or not content.strip():
            return _error("write_org_memory", "Provide content.")
        if not category or not category.strip():
            return _error("write_org_memory", "Provide category.")

        memory_id = create_org_memory(
            org_id,
            content.strip(),
            category.strip(),
            created_by=created_by,
            access_token=access_token,
        )
        return _success("write_org_memory", {"memory_id": memory_id, "org_id": org_id})

    def _build_profile_summary(
        self,
        *,
        access_token: str,
        user_id: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        products = get_all_products(access_token)
        engagements = get_all_engagements(access_token)
        active_engagements = [
            e for e in engagements if e.status.lower() in _ACTIVE_ENGAGEMENT_STATUSES
        ]

        org = get_user_org(access_token)
        org_info: dict[str, Any] | None = None
        member_count = 0
        if org:
            members = list_members(org.id, access_token)
            member_count = len(members)
            org_info = {
                "id": org.id,
                "name": org.name,
                "member_count": member_count,
            }

        summary = _compose_profile_summary(
            products=products,
            active_engagement_count=len(active_engagements),
            org=org,
            member_count=member_count,
        )

        return _success(
            "build_profile_summary",
            {
                "summary": summary,
                "product_count": len(products),
                "engagement_count": len(active_engagements),
                "org": org_info,
                "user_id": user_id,
            },
        )


def _compose_profile_summary(
    *,
    products: list[dict],
    active_engagement_count: int,
    org: Any | None,
    member_count: int,
) -> str:
    parts: list[str] = []

    if products:
        product_bits = []
        for product in products:
            total = product.get("total_kg_co2e")
            total_text = f"{total:.1f} kg CO2e" if total is not None else "unknown total"
            date = product.get("analysis_date") or "unknown date"
            product_bits.append(
                f"{product['product_name']} ({total_text}, {date})"
            )
        parts.append(
            f"User has analyzed {len(products)} product"
            f"{'' if len(products) == 1 else 's'}: {', '.join(product_bits)}."
        )
    else:
        parts.append("No saved product analyses yet.")

    if active_engagement_count:
        parts.append(
            f"{active_engagement_count} active supplier engagement"
            f"{'' if active_engagement_count == 1 else 's'}."
        )
    else:
        parts.append("No active supplier engagements.")

    if org:
        parts.append(
            f"Member of {org.name} ({member_count} team member"
            f"{'' if member_count == 1 else 's'})."
        )

    return " ".join(parts)


def _user_memory_dict(memory: UserMemory) -> dict[str, Any]:
    return {
        "memory_id": memory.memory_id,
        "user_id": memory.user_id,
        "content": memory.content,
        "category": memory.category,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }


def _org_memory_dict(memory: OrgMemory) -> dict[str, Any]:
    return {
        "memory_id": memory.memory_id,
        "org_id": memory.org_id,
        "created_by": memory.created_by,
        "content": memory.content,
        "category": memory.category,
        "created_at": memory.created_at,
        "updated_at": memory.updated_at,
    }


def _success(action: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"action": action, "success": True, "data": data}


def _error(action: str, message: str) -> dict[str, Any]:
    return {"action": action, "success": False, "error": message}


memory_skill = MemorySkill()
