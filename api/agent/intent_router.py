"""Intent routing via Claude tool use over the four platform skills."""

from __future__ import annotations

import copy
import time
from typing import Any

import anthropic
from dotenv import load_dotenv

from api.skills.registry import registry
from observability.logger import log_llm_call

load_dotenv()

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024

_INTERNAL_TOOL_FIELDS = frozenset(
    {"access_token", "user_id", "created_by", "session_id", "org_id"}
)


def _sanitize_tool_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove auth/internal fields so the LLM cannot see or invent them."""
    sanitized = copy.deepcopy(schema)
    properties = sanitized.get("properties", {})
    for field in _INTERNAL_TOOL_FIELDS:
        properties.pop(field, None)
    sanitized["properties"] = properties
    required = sanitized.get("required", [])
    sanitized["required"] = [name for name in required if name not in _INTERNAL_TOOL_FIELDS]
    return sanitized


def _build_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": schema["name"],
            "description": schema["description"],
            "input_schema": _sanitize_tool_schema(schema["input_schema"]),
        }
        for schema in registry.get_all_schemas()
    ]


async def route_intent(
    system_prompt: str,
    messages: list[dict[str, str]],
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Route the latest user message to a skill or a direct text response.

    Returns:
        {"type": "skill", "skill": str, "params": dict}
        or {"type": "text", "content": str}
    """
    client = anthropic.AsyncAnthropic()
    t0 = time.perf_counter()

    try:
        response = await client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=system_prompt,
            tools=_build_tools(),
            messages=_normalize_messages(messages),
        )
    except anthropic.APIError as exc:
        log_llm_call(
            app_name="platform_agent",
            tool_name="intent_router",
            model=_MODEL,
            tokens_in=None,
            tokens_out=None,
            latency_seconds=time.perf_counter() - t0,
            rag_used=False,
            error=str(exc),
            session_id=session_id,
        )
        return {
            "type": "text",
            "content": (
                "I'm having trouble processing your request right now. "
                "Please try again in a moment."
            ),
        }

    log_llm_call(
        app_name="platform_agent",
        tool_name="intent_router",
        model=_MODEL,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        latency_seconds=time.perf_counter() - t0,
        rag_used=False,
        session_id=session_id,
    )

    if response.stop_reason == "tool_use":
        tool_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None,
        )
        if tool_block is not None:
            params = tool_block.input if isinstance(tool_block.input, dict) else {}
            return {
                "type": "skill",
                "skill": tool_block.name,
                "params": params,
            }

    text = _extract_text(response.content)
    return {"type": "text", "content": text}


def _normalize_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role")
        content = message.get("content", "")
        if role in ("user", "assistant") and content:
            normalized.append({"role": role, "content": content})
    return normalized


def _extract_text(content: list[Any]) -> str:
    parts = [block.text for block in content if getattr(block, "type", None) == "text"]
    return "\n".join(parts).strip()
