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
    parse_response = client.post("/api/analyze/parse", files=files)
    assert parse_response.status_code == 200
    session_id = parse_response.json()["session_id"]

    match_response = client.post("/api/analyze/match-factors", json={"session_id": session_id})
    assert match_response.status_code == 200
    assert match_response.json()["warnings"] == []

    calc_response = client.post("/api/analyze/calculate", json={"session_id": session_id})
    assert calc_response.status_code == 200
    payload = calc_response.json()
    assert payload["result"]["total_kg_co2e"] == 20.0
    assert payload["result"]["matched_count"] == 1


def test_advisor_chat_uses_business_client(monkeypatch) -> None:
    monkeypatch.setattr("api.routes.advisor.build_llm_context", lambda: "Saved product context")

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
    )
    assert plan_response.status_code == 200
    session_id = plan_response.json()["session_id"]

    execute_response = client.post("/api/gap-analysis/execute", json={"session_id": session_id})
    assert execute_response.status_code == 200
    assert execute_response.json()["phase"] == "checkpoint"

    approve_response = client.post(
        "/api/gap-analysis/approve",
        json={"session_id": session_id, "action": "continue"},
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
        lambda product_name, top_n=10: SuppliersListResult(
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

    suppliers_response = client.get("/api/copilot/suppliers", params={"product_name": "Test"})
    assert suppliers_response.status_code == 200
    candidate_payload = suppliers_response.json()["candidates"][0]

    draft_response = client.post(
        "/api/copilot/draft-email",
        json={"product_name": "Test", "candidate": candidate_payload},
    )

    assert draft_response.status_code == 200
    assert draft_response.json()["draft"]["subject"] == "Scope 3 data request"
