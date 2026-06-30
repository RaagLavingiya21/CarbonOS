"""LangGraph workflow for the platform chat agent."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Literal

import anthropic
from dotenv import load_dotenv
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from api.agent.context_manager import build_conversation_context
from api.agent.intent_router import route_intent
from api.agent.state import AgentState
from api.agent.system_prompt import build_system_prompt
from api.skills.registry import registry
from db.chat_store import create_message, touch_thread
from db.database_url import get_database_url
from db.memory_store import create_user_memory
from observability.logger import log_llm_call

load_dotenv()

_SYNTHESIS_MODEL = "claude-sonnet-4-6"
_SUGGESTIONS_MODEL = "claude-haiku-4-5-20251001"

_DEFAULT_SUGGESTIONS = [
    "Analyze a bill of materials",
    "Run a Scope 3 gap analysis",
    "Start supplier engagement",
]

_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_cm: Any = None
_compiled_graph: Any = None


_INTAKE_LAUNCH_MESSAGES: dict[str, str] = {
    "bom_analyzer": (
        "I've opened the BOM Analyzer intake form below — upload your bill of "
        "materials and enter a product name to continue."
    ),
    "gap_analyzer": (
        "I've opened the Gap Analyzer intake form below — fill in your company "
        "profile to continue."
    ),
    "supplier_copilot": (
        "I've opened the Supplier Copilot intake form below — select a product "
        "and number of suppliers to rank."
    ),
}


def _build_workflow() -> StateGraph:
    """Build the uncompiled StateGraph (no checkpointer required)."""
    builder = StateGraph(AgentState)

    builder.add_node("build_context", _build_context_node)
    builder.add_node("route_intent", _route_intent_node)
    builder.add_node("execute_skill", _execute_skill_node)
    builder.add_node("format_response", _format_response_node)
    builder.add_node("generate_suggestions", _generate_suggestions_node)
    builder.add_node("save_to_history", _save_to_history_node)
    builder.add_node("evaluate_memory", _evaluate_memory_node)

    builder.add_edge(START, "build_context")
    builder.add_edge("build_context", "route_intent")
    builder.add_conditional_edges(
        "route_intent",
        _route_after_intent,
        {
            "execute_skill": "execute_skill",
            "format_response": "format_response",
        },
    )
    builder.add_edge("execute_skill", "generate_suggestions")
    builder.add_edge("format_response", "generate_suggestions")
    builder.add_edge("generate_suggestions", "save_to_history")
    builder.add_edge("save_to_history", "evaluate_memory")
    builder.add_edge("evaluate_memory", END)

    return builder


async def _get_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _checkpointer_cm
    if _checkpointer is None:
        db_url = get_database_url()
        if not db_url:
            raise RuntimeError(
                "DATABASE_URL is required for the agent graph PostgresSaver checkpointer"
            )
        _checkpointer_cm = AsyncPostgresSaver.from_conn_string(db_url)
        _checkpointer = await _checkpointer_cm.__aenter__()
        await _checkpointer.setup()
    return _checkpointer


async def get_agent_graph():
    """Return the compiled agent graph with PostgresSaver checkpointer."""
    global _compiled_graph
    if _compiled_graph is None:
        checkpointer = await _get_checkpointer()
        _compiled_graph = _build_workflow().compile(checkpointer=checkpointer)
    return _compiled_graph


async def ainvoke_agent(
    messages: list[dict[str, str]],
    user_id: str,
    access_token: str,
    thread_id: str | None = None,
) -> dict[str, Any]:
    """Invoke the agent graph and return the final state."""
    graph = await get_agent_graph()
    config = {"configurable": {"thread_id": thread_id or "ephemeral"}}
    return await graph.ainvoke(
        {
            "messages": messages,
            "user_id": user_id,
            "access_token": access_token,
            "thread_id": thread_id,
        },
        config=config,
    )


async def _build_context_node(state: AgentState) -> dict[str, Any]:
    system_prompt = await build_system_prompt(
        state["user_id"],
        state["access_token"],
    )
    context_layers = dict(state.get("context_layers") or {})
    context_layers["system_prompt"] = system_prompt

    thread_id = state.get("thread_id")
    if not thread_id:
        return {"context_layers": context_layers}

    conversation_context = await build_conversation_context(
        thread_id,
        state["access_token"],
    )

    if conversation_context.summary:
        context_layers["system_prompt"] = (
            system_prompt
            + "\n\n## Conversation summary so far\n\n"
            + conversation_context.summary
        )

    incoming_messages = list(state.get("messages") or [])
    current_user_message: dict[str, str] | None = None
    if incoming_messages and incoming_messages[-1].get("role") == "user":
        current_user_message = incoming_messages[-1]

    windowed_messages = list(conversation_context.recent_messages)
    if current_user_message is not None:
        windowed_messages.append(current_user_message)

    return {
        "context_layers": context_layers,
        "messages": windowed_messages,
    }


async def _route_intent_node(state: AgentState) -> dict[str, Any]:
    system_prompt = state["context_layers"]["system_prompt"]
    result = await route_intent(
        system_prompt,
        state["messages"],
        session_id=state.get("thread_id"),
    )

    if result["type"] == "skill":
        return {
            "active_skill": result["skill"],
            "skill_params": result["params"],
            "assistant_content": "",
        }

    return {
        "active_skill": None,
        "skill_params": None,
        "assistant_content": result["content"],
    }


def _route_after_intent(
    state: AgentState,
) -> Literal["execute_skill", "format_response"]:
    if state.get("active_skill"):
        return "execute_skill"
    return "format_response"


async def _execute_skill_node(state: AgentState) -> dict[str, Any]:
    skill_name = state["active_skill"]
    if not skill_name:
        return {}

    skill = registry.get_skill(skill_name)
    if skill is None:
        return {
            "skill_result": {
                "success": False,
                "error": f"Unknown skill: {skill_name}",
            },
            "assistant_content": (
                f"I couldn't run the requested skill ({skill_name}). "
                "Please try rephrasing your question."
            ),
        }

    params = dict(state.get("skill_params") or {})
    params["access_token"] = state["access_token"]
    if state.get("user_id"):
        params.setdefault("user_id", state["user_id"])

    action = params.pop("action", None)
    if not action:
        return {
            "skill_result": {"success": False, "error": "Skill action missing."},
            "assistant_content": (
                "I couldn't determine which operation to run. "
                "Please try rephrasing your request."
            ),
        }

    skill_result = await skill.run(action=action, **params)

    module_launch = None
    data = skill_result.get("data") if isinstance(skill_result.get("data"), dict) else {}
    if isinstance(data, dict) and data.get("module_launch"):
        module_launch = data["module_launch"]

    if (
        skill_result.get("success")
        and isinstance(module_launch, dict)
        and module_launch.get("step") == "intake"
    ):
        module_type = module_launch.get("module_type", "")
        assistant_content = _INTAKE_LAUNCH_MESSAGES.get(
            str(module_type),
            "Please fill in the intake form below to continue.",
        )
        return {
            "skill_result": skill_result,
            "assistant_content": assistant_content,
            "module_launch": module_launch,
        }

    assistant_content = await _synthesize_skill_response(
        state["context_layers"]["system_prompt"],
        state["messages"],
        skill_result,
        session_id=state.get("thread_id"),
    )

    return {
        "skill_result": skill_result,
        "assistant_content": assistant_content,
        "module_launch": module_launch,
    }


async def _format_response_node(state: AgentState) -> dict[str, Any]:
    return {}


async def _generate_suggestions_node(state: AgentState) -> dict[str, Any]:
    suggestions = await _generate_suggestions(
        state.get("assistant_content", ""),
        state.get("messages", []),
        session_id=state.get("thread_id"),
    )
    return {"suggestions": suggestions}


def _save_to_history_node(state: AgentState) -> dict[str, Any]:
    thread_id = state.get("thread_id")
    if not thread_id:
        return {}

    access_token = state["access_token"]
    messages = state.get("messages") or []

    user_message = next(
        (message for message in reversed(messages) if message.get("role") == "user"),
        None,
    )
    if user_message and user_message.get("content"):
        create_message(
            thread_id,
            "user",
            user_message["content"],
            access_token=access_token,
        )

    metadata: dict[str, Any] = {}
    if state.get("active_skill"):
        metadata["skill"] = state["active_skill"]
    if state.get("module_launch"):
        metadata["module_launch"] = state["module_launch"]
    if state.get("suggestions"):
        metadata["suggestions"] = state["suggestions"]

    assistant_content = state.get("assistant_content", "")
    if assistant_content:
        create_message(
            thread_id,
            "assistant",
            assistant_content,
            access_token=access_token,
            metadata=metadata,
        )
        touch_thread(thread_id, access_token=access_token)

    return {}


async def _evaluate_memory_node(state: AgentState) -> dict[str, Any]:
    """Post-process a turn: decide whether to persist durable user preferences."""
    thread_id = state.get("thread_id")
    user_id = state.get("user_id")
    access_token = state.get("access_token")
    assistant_content = state.get("assistant_content", "")

    if not thread_id or not user_id or not access_token or not assistant_content:
        return {}

    user_message = _latest_user_message(state.get("messages") or [])
    if not user_message:
        return {}

    prompt = (
        f"User message: {user_message}\n"
        f"Assistant reply: {assistant_content}\n\n"
        "Should anything durable be saved to this user's long-term memory? "
        "Save only stable preferences, focus areas, or working patterns "
        "(e.g. 'focused on reducing packaging emissions', 'prefers metric tons'). "
        "Do NOT save transient chit-chat, one-off questions, or facts already "
        "in the platform database.\n\n"
        "Return only JSON with this shape:\n"
        '{"save": false, "content": "", "category": ""}\n'
        "category must be one of: preference, focus_area, working_pattern."
    )

    client = anthropic.AsyncAnthropic()
    t0 = time.perf_counter()
    try:
        response = await client.messages.create(
            model=_SUGGESTIONS_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        log_llm_call(
            app_name="platform_agent",
            tool_name="evaluate_memory",
            model=_SUGGESTIONS_MODEL,
            tokens_in=None,
            tokens_out=None,
            latency_seconds=time.perf_counter() - t0,
            rag_used=False,
            error=str(exc),
            session_id=thread_id,
        )
        return {}

    log_llm_call(
        app_name="platform_agent",
        tool_name="evaluate_memory",
        model=_SUGGESTIONS_MODEL,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        latency_seconds=time.perf_counter() - t0,
        rag_used=False,
        session_id=thread_id,
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    decision = _parse_memory_decision_json(text)
    if not decision or not decision.get("save"):
        return {}

    content = str(decision.get("content", "")).strip()
    category = str(decision.get("category", "")).strip()
    if not content or not category:
        return {}

    try:
        create_user_memory(
            content,
            category,
            user_id=user_id,
            access_token=access_token,
        )
    except Exception:
        return {}

    return {}


def _parse_memory_decision_json(text: str) -> dict[str, Any] | None:
    import re

    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


async def _synthesize_skill_response(
    system_prompt: str,
    messages: list[dict[str, str]],
    skill_result: dict[str, Any],
    *,
    session_id: str | None = None,
) -> str:
    if not skill_result.get("success"):
        error = skill_result.get("error", "The skill returned an error.")
        return f"I ran into an issue: {error}"

    client = anthropic.AsyncAnthropic()
    user_message = _latest_user_message(messages)
    skill_json = json.dumps(skill_result, indent=2, default=str)

    synthesis_messages = [
        {
            "role": "user",
            "content": (
                f"User question: {user_message}\n\n"
                f"Skill result:\n{skill_json}\n\n"
                "Write a clear, concise assistant reply grounded in the skill result. "
                "Cite specific numbers and sources when present. "
                "Do not invent data not in the skill result."
            ),
        }
    ]

    t0 = time.perf_counter()
    try:
        response = await client.messages.create(
            model=_SYNTHESIS_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=synthesis_messages,
        )
    except anthropic.APIError as exc:
        log_llm_call(
            app_name="platform_agent",
            tool_name="skill_synthesis",
            model=_SYNTHESIS_MODEL,
            tokens_in=None,
            tokens_out=None,
            latency_seconds=time.perf_counter() - t0,
            rag_used=False,
            error=str(exc),
            session_id=session_id,
        )
        return _fallback_skill_response(skill_result)

    log_llm_call(
        app_name="platform_agent",
        tool_name="skill_synthesis",
        model=_SYNTHESIS_MODEL,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        latency_seconds=time.perf_counter() - t0,
        rag_used=False,
        session_id=session_id,
    )

    text_blocks = [
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ]
    return "\n".join(text_blocks).strip() or _fallback_skill_response(skill_result)


async def _generate_suggestions(
    assistant_content: str,
    messages: list[dict[str, str]],
    *,
    session_id: str | None = None,
) -> list[str]:
    client = anthropic.AsyncAnthropic()
    user_message = _latest_user_message(messages)

    prompt = (
        f"User message: {user_message}\n"
        f"Assistant reply: {assistant_content}\n\n"
        "Suggest 2-3 short next-step prompts the user might click to continue their "
        "carbon footprint workflow (e.g. analyze BOM, gap analysis, supplier engagement). "
        "Return only a JSON array of strings, nothing else."
    )

    t0 = time.perf_counter()
    try:
        response = await client.messages.create(
            model=_SUGGESTIONS_MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as exc:
        log_llm_call(
            app_name="platform_agent",
            tool_name="generate_suggestions",
            model=_SUGGESTIONS_MODEL,
            tokens_in=None,
            tokens_out=None,
            latency_seconds=time.perf_counter() - t0,
            rag_used=False,
            error=str(exc),
            session_id=session_id,
        )
        return list(_DEFAULT_SUGGESTIONS)

    log_llm_call(
        app_name="platform_agent",
        tool_name="generate_suggestions",
        model=_SUGGESTIONS_MODEL,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        latency_seconds=time.perf_counter() - t0,
        rag_used=False,
        session_id=session_id,
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    suggestions = _parse_suggestions_json(text)
    if suggestions:
        return suggestions[:3]
    return list(_DEFAULT_SUGGESTIONS)


def _parse_suggestions_json(text: str) -> list[str]:
    import re

    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _latest_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def _fallback_skill_response(skill_result: dict[str, Any]) -> str:
    data = skill_result.get("data")
    if isinstance(data, dict):
        if "content" in data and isinstance(data["content"], str):
            return data["content"]
        if "summary" in data and isinstance(data["summary"], str):
            return data["summary"]
    return json.dumps(skill_result, indent=2, default=str)
