"""Rolling conversation context: last N messages verbatim + summary of older turns."""

from __future__ import annotations

import time
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv

from db import chat_store
from db.chat_store import ChatMessage
from observability.logger import log_llm_call

load_dotenv()

WINDOW_SIZE = 10
_SUMMARY_MODEL = "claude-haiku-4-5-20251001"
_ROLLING_SUMMARY_TYPE = "rolling_summary"


@dataclass
class ConversationContext:
    """Windowed conversation context for the agent."""

    summary: str | None
    recent_messages: list[dict[str, str]]


async def build_conversation_context(
    thread_id: str,
    access_token: str,
) -> ConversationContext:
    """Build bounded conversation context with a rolling summary of older messages."""
    all_messages = chat_store.list_messages(thread_id, access_token)
    convo = _conversation_messages(all_messages)
    existing_summary = _latest_rolling_summary(all_messages)

    if len(convo) <= WINDOW_SIZE:
        return ConversationContext(
            summary=existing_summary.content if existing_summary else None,
            recent_messages=_to_message_dicts(convo),
        )

    recent = convo[-WINDOW_SIZE:]
    older = convo[:-WINDOW_SIZE]
    summarized_count = _summarized_count(existing_summary)
    existing_text = existing_summary.content if existing_summary else None

    if existing_text and summarized_count >= len(older):
        return ConversationContext(
            summary=existing_text,
            recent_messages=_to_message_dicts(recent),
        )

    new_messages = older[summarized_count:]
    summary_text = await _summarize_messages(
        previous_summary=existing_text,
        new_messages=new_messages,
        thread_id=thread_id,
    )

    if not summary_text:
        summary_text = existing_text

    if summary_text and summary_text != existing_text:
        chat_store.create_message(
            thread_id,
            "system",
            summary_text,
            access_token=access_token,
            metadata={
                "type": _ROLLING_SUMMARY_TYPE,
                "summarized_count": len(older),
            },
        )

    return ConversationContext(
        summary=summary_text,
        recent_messages=_to_message_dicts(recent),
    )


def _conversation_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    return [message for message in messages if message.role in ("user", "assistant")]


def _latest_rolling_summary(messages: list[ChatMessage]) -> ChatMessage | None:
    summaries = [
        message
        for message in messages
        if message.role == "system"
        and message.metadata.get("type") == _ROLLING_SUMMARY_TYPE
    ]
    if not summaries:
        return None
    return max(summaries, key=lambda message: message.created_at)


def _summarized_count(summary: ChatMessage | None) -> int:
    if summary is None:
        return 0
    raw = summary.metadata.get("summarized_count", 0)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _to_message_dicts(messages: list[ChatMessage]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


def _format_transcript(messages: list[ChatMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.role.capitalize()
        lines.append(f"{role}: {message.content}")
    return "\n".join(lines)


async def _summarize_messages(
    *,
    previous_summary: str | None,
    new_messages: list[ChatMessage],
    thread_id: str,
) -> str | None:
    """Fold new aged-out messages into a single summary paragraph."""
    if not new_messages and not previous_summary:
        return None

    transcript = _format_transcript(new_messages)
    if previous_summary:
        user_prompt = (
            f"Previous conversation summary:\n{previous_summary}\n\n"
            f"New messages to incorporate:\n{transcript}\n\n"
            "Update the summary into a single concise paragraph that preserves "
            "key facts, decisions, product names, and user goals. "
            "Return only the updated summary paragraph, nothing else."
        )
    else:
        user_prompt = (
            f"Conversation messages to summarize:\n{transcript}\n\n"
            "Summarize these messages into a single concise paragraph that preserves "
            "key facts, decisions, product names, and user goals. "
            "Return only the summary paragraph, nothing else."
        )

    client = anthropic.AsyncAnthropic()
    t0 = time.perf_counter()
    try:
        response = await client.messages.create(
            model=_SUMMARY_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.APIError as exc:
        log_llm_call(
            app_name="platform_agent",
            tool_name="conversation_summary",
            model=_SUMMARY_MODEL,
            tokens_in=None,
            tokens_out=None,
            latency_seconds=time.perf_counter() - t0,
            rag_used=False,
            error=str(exc),
            session_id=thread_id,
        )
        return previous_summary

    log_llm_call(
        app_name="platform_agent",
        tool_name="conversation_summary",
        model=_SUMMARY_MODEL,
        tokens_in=response.usage.input_tokens,
        tokens_out=response.usage.output_tokens,
        latency_seconds=time.perf_counter() - t0,
        rag_used=False,
        session_id=thread_id,
    )

    text_blocks = [
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ]
    summary = "\n".join(text_blocks).strip()
    return summary or previous_summary
