from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from copilot.models import (
    EmailDraft,
    EmailDraftResult,
    EngagementCandidate,
    SuppliersListResult,
)
from factors.ef_lookup import EFMatch
from gap_analyzer.models import CompanyProfile, Plan, PlanStep, ToolResult
from llm.client import AdvisorResponse
from tests.conftest import AUTH_HEADERS

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyzer_checkpoint_flow(monkeypatch) -> None:
    def fake_lookup(material: str, country: str | None = None) -> EFMatch:
        return EFMatch(
            material_input=material,
            sector_name="Cotton farming",
            sector_code="1119A0",
            ef_kg_co2e_per_usd=2.0,
            country_used=country or "USA",
            confidence_score=100.0,
            is_low_confidence=False,
            is_no_match=False,
            source_citation="Test factor",
            suggested_alternatives=[],
        )

    monkeypatch.setattr("api.routes.analyzer.lookup_ef", fake_lookup)

    files = {
        "file": (
            "test_product.csv",
            "component,material,quantity,spend_usd\nbody,cotton,1,10\n",
            "text/csv",
        )
    }
    parse_response = client.post("/api/analyze/parse", files=files, headers=AUTH_HEADERS)
    assert parse_response.status_code == 200
    session_id = parse_response.json()["session_id"]

    match_response = client.post(
        "/api/analyze/match-factors",
        json={"session_id": session_id},
        headers=AUTH_HEADERS,
    )
    assert match_response.status_code == 200
    assert match_response.json()["warnings"] == []

    calc_response = client.post(
        "/api/analyze/calculate",
        json={"session_id": session_id},
        headers=AUTH_HEADERS,
    )
    assert calc_response.status_code == 200
    payload = calc_response.json()
    assert payload["result"]["total_kg_co2e"] == 20.0
    assert payload["result"]["matched_count"] == 1


def test_advisor_chat_uses_business_client(monkeypatch) -> None:
    monkeypatch.setattr(
        "api.routes.advisor.build_llm_context",
        lambda access_token: "Saved product context",
    )

    def fake_ask_advisor(**kwargs) -> AdvisorResponse:
        return AdvisorResponse(
            content="The test product totals 20 kg CO2e.",
            has_data_reference=True,
            citations=["Test citation"],
        )

    monkeypatch.setattr("api.routes.advisor.ask_advisor", fake_ask_advisor)

    response = client.post(
        "/api/advisor/chat",
        json={"user_message": "What is my footprint?", "conversation_history": []},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["content"] == "The test product totals 20 kg CO2e."
    assert response.json()["citations"] == ["Test citation"]


def test_gap_analysis_plan_execute_approve(monkeypatch) -> None:
    plan = Plan(
        steps=[
            PlanStep(
                step_num=1,
                tool_name="assess_reporting_requirements",
                rationale="Test rationale",
                has_checkpoint_after=True,
            )
        ],
        raw_plan_text="Test plan",
    )

    monkeypatch.setattr(
        "api.graphs.gap_analyzer_graph.generate_plan",
        lambda profile, session_id=None: plan,
    )

    def fake_execute_step(
        step: PlanStep,
        company_profile: CompanyProfile,
        previous_results: dict[str, ToolResult],
        call_counts: dict[str, int],
        session_id: str | None = None,
    ) -> ToolResult:
        return ToolResult(
            tool_name=step.tool_name,
            content="Checkpoint content",
            structured={"ok": True},
            citations=["GHG Protocol"],
        )

    monkeypatch.setattr("api.graphs.gap_analyzer_graph.execute_step", fake_execute_step)

    plan_response = client.post(
        "/api/gap-analysis/plan",
        json={
            "profile": {
                "name": "ACME",
                "size": "500-5,000 employees",
                "sector": "apparel",
                "geography": "United States",
                "products": "shirts",
            }
        },
        headers=AUTH_HEADERS,
    )
    assert plan_response.status_code == 200
    session_id = plan_response.json()["session_id"]

    execute_response = client.post(
        "/api/gap-analysis/execute",
        json={"session_id": session_id},
        headers=AUTH_HEADERS,
    )
    assert execute_response.status_code == 200
    assert execute_response.json()["phase"] == "checkpoint"

    approve_response = client.post(
        "/api/gap-analysis/approve",
        json={"session_id": session_id, "action": "continue"},
        headers=AUTH_HEADERS,
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["phase"] == "done"


def test_copilot_suppliers_and_draft(monkeypatch) -> None:
    candidate = EngagementCandidate(
        supplier_name="FiberTex Global",
        component="body",
        material="cotton",
        kg_co2e=20.0,
        share_pct=100.0,
        contact_found=True,
        contact_name="Sarah Chen",
        contact_email="sarah@example.com",
        existing_engagement_id=None,
        engagement_status="new",
    )
    monkeypatch.setattr(
        "api.routes.copilot.get_suppliers_list",
        lambda product_name, top_n=10, access_token=None: SuppliersListResult(
            candidates=[candidate],
            product_name=product_name,
        ),
    )
    monkeypatch.setattr(
        "api.graphs.supplier_copilot_graph.draft_email_run",
        lambda candidate, product_name, session_id=None: EmailDraftResult(
            draft=EmailDraft(
                to="sarah@example.com",
                subject="Scope 3 data request",
                body="Please provide primary emissions data.",
                ghg_protocol_basis="GHG Protocol Chapter 7.",
            ),
            citations=["GHG Protocol Chapter 7"],
        ),
    )

    suppliers_response = client.get(
        "/api/copilot/suppliers",
        params={"product_name": "Test"},
        headers=AUTH_HEADERS,
    )
    assert suppliers_response.status_code == 200
    candidate_payload = suppliers_response.json()["candidates"][0]

    draft_response = client.post(
        "/api/copilot/draft-email",
        json={"product_name": "Test", "candidate": candidate_payload},
        headers=AUTH_HEADERS,
    )

    assert draft_response.status_code == 200
    assert draft_response.json()["draft"]["subject"] == "Scope 3 data request"


def test_protected_route_requires_auth() -> None:
    response = client.post(
        "/api/advisor/chat",
        json={"user_message": "Hello", "conversation_history": []},
    )
    assert response.status_code == 401


def test_chat_thread_crud_and_send_message(monkeypatch) -> None:
    thread_id = "11111111-1111-1111-1111-111111111111"
    thread = {
        "thread_id": thread_id,
        "user_id": "00000000-0000-0000-0000-000000000001",
        "org_id": None,
        "title": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "deleted_at": None,
    }

    class FakeThread:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    fake_thread = FakeThread(**thread)
    stored_messages: list[dict] = []

    monkeypatch.setattr(
        "api.routes.chat.chat_store.create_thread",
        lambda **kwargs: thread_id,
    )
    monkeypatch.setattr(
        "api.routes.chat.chat_store.get_thread",
        lambda tid, access_token: fake_thread if tid == thread_id else None,
    )
    monkeypatch.setattr(
        "api.routes.chat.chat_store.list_threads",
        lambda access_token: [fake_thread],
    )
    monkeypatch.setattr(
        "api.routes.chat.chat_store.list_messages",
        lambda tid, access_token: stored_messages,
    )
    monkeypatch.setattr(
        "api.routes.chat.chat_store.delete_thread",
        lambda tid, access_token: None,
    )

    async def fake_ainvoke_agent(messages, user_id, access_token, thread_id=None):
        stored_messages.extend(
            [
                {"role": "user", "content": messages[-1]["content"]},
                {"role": "assistant", "content": "Hello from the agent."},
            ]
        )
        return {
            "assistant_content": "Hello from the agent.",
            "suggestions": ["Analyze a bill of materials"],
            "module_launch": None,
        }

    monkeypatch.setattr("api.routes.chat.ainvoke_agent", fake_ainvoke_agent)

    create_response = client.post("/api/chat/threads", json={}, headers=AUTH_HEADERS)
    assert create_response.status_code == 200
    assert create_response.json()["thread_id"] == thread_id

    list_response = client.get("/api/chat/threads", headers=AUTH_HEADERS)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = client.get(f"/api/chat/threads/{thread_id}", headers=AUTH_HEADERS)
    assert detail_response.status_code == 200
    assert detail_response.json()["thread"]["thread_id"] == thread_id

    message_response = client.post(
        f"/api/chat/threads/{thread_id}/messages",
        json={"content": "What is Scope 3?"},
        headers=AUTH_HEADERS,
    )
    assert message_response.status_code == 200
    payload = message_response.json()
    assert payload["content"] == "Hello from the agent."
    assert payload["suggestions"] == ["Analyze a bill of materials"]
    assert payload["module_launch"] is None

    delete_response = client.delete(
        f"/api/chat/threads/{thread_id}",
        headers=AUTH_HEADERS,
    )
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True}


def test_panel_crud(monkeypatch) -> None:
    panel_id = "22222222-2222-2222-2222-222222222222"
    panel_state = {"step": "review"}

    class FakePanel:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    fake_panel = FakePanel(
        panel_id=panel_id,
        user_id="00000000-0000-0000-0000-000000000001",
        thread_id=None,
        module_type="bom_analyzer",
        panel_state=panel_state,
        tab_order=0,
        is_active=True,
        created_at="2024-01-01T00:00:00+00:00",
        updated_at="2024-01-01T00:00:00+00:00",
    )

    def fake_get_panel(pid, access_token):
        return fake_panel if pid == panel_id else None

    monkeypatch.setattr(
        "api.routes.panels.panel_store.create_panel",
        lambda module_type, **kwargs: panel_id,
    )
    monkeypatch.setattr("api.routes.panels.panel_store.get_panel", fake_get_panel)
    monkeypatch.setattr(
        "api.routes.panels.panel_store.list_panels",
        lambda access_token: [fake_panel],
    )

    def fake_update_panel(pid, access_token, **fields):
        if "panel_state" in fields:
            fake_panel.panel_state = fields["panel_state"]
        if "tab_order" in fields:
            fake_panel.tab_order = fields["tab_order"]
        if "is_active" in fields:
            fake_panel.is_active = fields["is_active"]

    monkeypatch.setattr("api.routes.panels.panel_store.update_panel", fake_update_panel)
    monkeypatch.setattr(
        "api.routes.panels.panel_store.delete_panel",
        lambda pid, access_token: None,
    )

    create_response = client.post(
        "/api/panels",
        json={"module_type": "bom_analyzer", "panel_state": panel_state},
        headers=AUTH_HEADERS,
    )
    assert create_response.status_code == 200
    assert create_response.json()["module_type"] == "bom_analyzer"

    list_response = client.get("/api/panels", headers=AUTH_HEADERS)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    patch_response = client.patch(
        f"/api/panels/{panel_id}",
        json={"panel_state": {"step": "results"}, "tab_order": 1},
        headers=AUTH_HEADERS,
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["panel_state"] == {"step": "results"}
    assert patch_response.json()["tab_order"] == 1

    delete_response = client.delete(f"/api/panels/{panel_id}", headers=AUTH_HEADERS)
    assert delete_response.status_code == 200
    assert delete_response.json() == {"deleted": True}
