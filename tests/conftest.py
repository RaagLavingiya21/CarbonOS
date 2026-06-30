from __future__ import annotations

import pytest

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_ACCESS_TOKEN = "test-access-token"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_ACCESS_TOKEN}"}


@pytest.fixture(autouse=True)
def bypass_supabase_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bypass JWT verification in API tests."""

    def fake_verify(_token: str) -> str:
        return TEST_USER_ID

    monkeypatch.setattr("api.middleware.auth.verify_supabase_jwt", fake_verify)


@pytest.fixture(autouse=True)
def use_memory_checkpointer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use in-memory LangGraph checkpointer in tests — no Postgres required."""
    from langgraph.checkpoint.memory import MemorySaver

    import api.graphs.gap_analyzer_graph as gap_graph
    import api.graphs.supplier_copilot_graph as copilot_graph

    memory = MemorySaver()
    monkeypatch.setattr("api.graphs.checkpointer.get_checkpointer", lambda: memory)
    monkeypatch.setattr(gap_graph, "get_checkpointer", lambda: memory)
    monkeypatch.setattr(copilot_graph, "get_checkpointer", lambda: memory)
    gap_graph._gap_analyzer_graph = None
    copilot_graph._email_draft_graph = None
    copilot_graph._response_routing_graph = None


@pytest.fixture(autouse=True)
def disable_live_thread_title_generation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid real Anthropic calls during API tests (CI may inject repo secrets)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    async def fake_generate_thread_title(
        first_message: str,
        *,
        session_id: str | None = None,
    ) -> str | None:
        return None

    monkeypatch.setattr(
        "api.routes.chat._generate_thread_title",
        fake_generate_thread_title,
    )
