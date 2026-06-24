"""Pydantic request and response models for the FastAPI layer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from calc.critic import CriticFinding, CriticReport
from calc.footprint import FootprintResult, LineItem
from copilot.models import (
    EmailDraft,
    EmailDraftResult,
    EngagementCandidate,
    ParsedResponse,
    ParseResponseResult,
    RoutingDecision,
    RoutingResult,
    SuppliersListResult,
)
from factors.ef_lookup import EFMatch
from gap_analyzer.models import CompanyProfile, Plan, PlanStep, ToolResult
from parsing.bom_parser import BOMFlag, BOMRow, ParsedBOM


class HealthResponse(BaseModel):
    status: str


class ErrorResponse(BaseModel):
    detail: str


# Analyzer models


class BOMFlagDTO(BaseModel):
    row_index: int
    field: str
    flag_type: str
    message: str
    severity: str

    @classmethod
    def from_domain(cls, flag: BOMFlag) -> "BOMFlagDTO":
        return cls(**flag.__dict__)


class BOMRowDTO(BaseModel):
    row_index: int
    component: str | None
    material: str | None
    quantity: float | None
    spend_usd: float | None
    weight_kg: float | None
    supplier: str | None
    country_of_origin: str | None
    flags: list[BOMFlagDTO] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, row: BOMRow) -> "BOMRowDTO":
        return cls(
            row_index=row.row_index,
            component=row.component,
            material=row.material,
            quantity=row.quantity,
            spend_usd=row.spend_usd,
            weight_kg=row.weight_kg,
            supplier=row.supplier,
            country_of_origin=row.country_of_origin,
            flags=[BOMFlagDTO.from_domain(flag) for flag in row.flags],
        )


class ParsedBOMDTO(BaseModel):
    product_name: str
    rows: list[BOMRowDTO]
    file_errors: list[str]
    is_valid: bool
    flagged_row_indices: list[int]
    all_flags: list[BOMFlagDTO]

    @classmethod
    def from_domain(cls, bom: ParsedBOM) -> "ParsedBOMDTO":
        return cls(
            product_name=bom.product_name,
            rows=[BOMRowDTO.from_domain(row) for row in bom.rows],
            file_errors=bom.file_errors,
            is_valid=bom.is_valid,
            flagged_row_indices=sorted(bom.flagged_row_indices),
            all_flags=[BOMFlagDTO.from_domain(flag) for flag in bom.all_flags],
        )


class EFMatchDTO(BaseModel):
    material_input: str
    sector_name: str
    sector_code: str
    ef_kg_co2e_per_usd: float
    country_used: str
    confidence_score: float
    is_low_confidence: bool
    is_no_match: bool
    source_citation: str
    suggested_alternatives: list[str]

    @classmethod
    def from_domain(cls, match: EFMatch | None) -> "EFMatchDTO | None":
        if match is None:
            return None
        return cls(**match.__dict__)


class LineItemDTO(BaseModel):
    row_index: int
    component: str | None
    material: str | None
    quantity: float | None
    spend_usd: float | None
    weight_kg: float | None
    supplier: str | None
    country_of_origin: str | None
    sector_name: str
    sector_code: str
    ef_kg_co2e_per_usd: float
    ef_source: str
    ef_confidence: float
    kg_co2e: float
    share_pct: float
    is_matched: bool
    is_low_confidence: bool
    is_no_ef_match: bool
    is_flagged_by_parser: bool

    @classmethod
    def from_domain(cls, item: LineItem) -> "LineItemDTO":
        return cls(**item.__dict__)


class FootprintResultDTO(BaseModel):
    product_name: str
    total_kg_co2e: float
    line_items: list[LineItemDTO]
    matched_count: int
    flagged_count: int
    unmatched_count: int
    completeness_pct: float
    has_any_results: bool
    hotspots: list[LineItemDTO]

    @classmethod
    def from_domain(cls, result: FootprintResult) -> "FootprintResultDTO":
        return cls(
            product_name=result.product_name,
            total_kg_co2e=result.total_kg_co2e,
            line_items=[LineItemDTO.from_domain(item) for item in result.line_items],
            matched_count=result.matched_count,
            flagged_count=result.flagged_count,
            unmatched_count=result.unmatched_count,
            completeness_pct=result.completeness_pct,
            has_any_results=result.has_any_results,
            hotspots=[LineItemDTO.from_domain(item) for item in result.hotspots],
        )


class CriticFindingDTO(BaseModel):
    check: str
    severity: str
    message: str
    row_index: int | None = None

    @classmethod
    def from_domain(cls, finding: CriticFinding) -> "CriticFindingDTO":
        return cls(**finding.__dict__)


class CriticReportDTO(BaseModel):
    findings: list[CriticFindingDTO]
    total_was_corrected: bool
    original_total: float | None
    has_findings: bool
    correction_count: int
    warning_count: int

    @classmethod
    def from_domain(cls, report: CriticReport) -> "CriticReportDTO":
        return cls(
            findings=[CriticFindingDTO.from_domain(finding) for finding in report.findings],
            total_was_corrected=report.total_was_corrected,
            original_total=report.original_total,
            has_findings=report.has_findings,
            correction_count=report.correction_count,
            warning_count=report.warning_count,
        )


class ParseBOMResponse(BaseModel):
    session_id: str
    phase: Literal["bom_review"]
    bom: ParsedBOMDTO


class MatchFactorsRequest(BaseModel):
    session_id: str


class MatchFactorsResponse(BaseModel):
    session_id: str
    phase: Literal["ef_review"]
    ef_matches: list[EFMatchDTO | None]
    warnings: list[str]


class CalculateFootprintRequest(BaseModel):
    session_id: str


class CalculateFootprintResponse(BaseModel):
    session_id: str
    phase: Literal["calc_review"]
    result: FootprintResultDTO
    critic_report: CriticReportDTO


class SaveAnalysisRequest(BaseModel):
    session_id: str
    product_name: str
    status: Literal["approved", "flagged"] = "approved"
    flagged_comment: str | None = None


class SaveAnalysisResponse(BaseModel):
    product_id: int
    phase: Literal["saved"]


class AnalyzeResponse(BaseModel):
    session_id: str
    phase: Literal["calc_review", "saved"]
    bom: ParsedBOMDTO
    ef_matches: list[EFMatchDTO | None]
    warnings: list[str]
    result: FootprintResultDTO
    critic_report: CriticReportDTO
    product_id: int | None = None


class AnalysisSummaryDTO(BaseModel):
    product_id: int
    product_name: str
    analysis_date: str
    total_kg_co2e: float
    matched_items: int
    flagged_items: int
    status: str | None = None
    flagged_comment: str | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AnalysisSummaryDTO":
        return cls(**{k: v for k, v in row.items() if k in cls.model_fields})


class AnalysisLineItemDTO(BaseModel):
    component: str | None
    material: str | None
    spend_usd: float | None
    matched_sector: str | None
    emission_factor: float | None
    ef_source: str | None
    kg_co2e: float | None
    share_pct: float | None
    flag_status: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AnalysisLineItemDTO":
        return cls(**row)


class AnalysisDetailDTO(AnalysisSummaryDTO):
    line_items: list[AnalysisLineItemDTO] = Field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AnalysisDetailDTO":
        data = {k: v for k, v in row.items() if k in cls.model_fields}
        data["line_items"] = [
            AnalysisLineItemDTO.from_row(item) for item in row.get("line_items", [])
        ]
        return cls(**data)


class DeleteSessionResponse(BaseModel):
    deleted: bool


# Advisor models


class MessageDTO(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AdvisorChatRequest(BaseModel):
    user_message: str
    conversation_history: list[MessageDTO] = Field(default_factory=list)
    session_id: str | None = None


class AdvisorChatResponse(BaseModel):
    session_id: str
    content: str
    has_data_reference: bool
    citations: list[str]
    error: str | None = None


# Gap analyzer models


class CompanyProfileDTO(BaseModel):
    name: str = "Unknown company"
    size: str
    sector: str
    geography: str = "Not specified"
    products: str

    def to_domain(self) -> CompanyProfile:
        return CompanyProfile(
            name=self.name.strip() or "Unknown company",
            size=self.size,
            sector=self.sector.strip(),
            geography=self.geography.strip() or "Not specified",
            products=self.products.strip(),
        )

    @classmethod
    def from_domain(cls, profile: CompanyProfile) -> "CompanyProfileDTO":
        return cls(**profile.__dict__)


class PlanStepDTO(BaseModel):
    step_num: int
    tool_name: str
    rationale: str
    has_checkpoint_after: bool

    @classmethod
    def from_domain(cls, step: PlanStep) -> "PlanStepDTO":
        return cls(**step.__dict__)


class PlanDTO(BaseModel):
    steps: list[PlanStepDTO]
    raw_plan_text: str

    @classmethod
    def from_domain(cls, plan: Plan) -> "PlanDTO":
        return cls(
            steps=[PlanStepDTO.from_domain(step) for step in plan.steps],
            raw_plan_text=plan.raw_plan_text,
        )


class ToolResultDTO(BaseModel):
    tool_name: str
    content: str
    structured: dict[str, Any]
    citations: list[str]
    error: str | None = None

    @classmethod
    def from_domain(cls, result: ToolResult) -> "ToolResultDTO":
        return cls(**result.__dict__)


class GapPlanRequest(BaseModel):
    profile: CompanyProfileDTO
    session_id: str | None = None


class GapPlanResponse(BaseModel):
    session_id: str
    phase: Literal["planning"]
    profile: CompanyProfileDTO
    plan: PlanDTO
    current_step: int


class GapExecuteRequest(BaseModel):
    session_id: str


class GapExecuteResponse(BaseModel):
    session_id: str
    phase: Literal["executing", "checkpoint", "done"]
    current_step: int
    result: ToolResultDTO | None = None
    results: dict[str, ToolResultDTO] = Field(default_factory=dict)


class GapApproveRequest(BaseModel):
    session_id: str
    action: Literal["continue", "stop"] = "continue"


class GapApproveResponse(BaseModel):
    session_id: str
    phase: Literal["executing", "done"]
    current_step: int


class GapReportResponse(BaseModel):
    session_id: str
    profile: CompanyProfileDTO
    markdown: str
    results: dict[str, ToolResultDTO]


# Supplier copilot models


class EngagementCandidateDTO(BaseModel):
    supplier_name: str
    component: str | None
    material: str | None
    kg_co2e: float | None
    share_pct: float | None
    contact_found: bool
    contact_name: str | None
    contact_email: str | None
    existing_engagement_id: int | None
    engagement_status: str

    def to_domain(self) -> EngagementCandidate:
        return EngagementCandidate(**self.model_dump())

    @classmethod
    def from_domain(cls, candidate: EngagementCandidate) -> "EngagementCandidateDTO":
        return cls(**candidate.__dict__)


class SuppliersListResponse(BaseModel):
    product_name: str
    candidates: list[EngagementCandidateDTO]
    error: str | None = None

    @classmethod
    def from_domain(cls, result: SuppliersListResult) -> "SuppliersListResponse":
        return cls(
            product_name=result.product_name,
            candidates=[EngagementCandidateDTO.from_domain(c) for c in result.candidates],
            error=result.error,
        )


class EmailDraftDTO(BaseModel):
    to: str
    subject: str
    body: str
    ghg_protocol_basis: str

    @classmethod
    def from_domain(cls, draft: EmailDraft) -> "EmailDraftDTO":
        return cls(**draft.__dict__)


class EmailDraftResultDTO(BaseModel):
    draft: EmailDraftDTO | None
    citations: list[str]
    error: str | None = None

    @classmethod
    def from_domain(cls, result: EmailDraftResult) -> "EmailDraftResultDTO":
        return cls(
            draft=EmailDraftDTO.from_domain(result.draft) if result.draft else None,
            citations=result.citations,
            error=result.error,
        )


class DraftEmailRequest(BaseModel):
    product_name: str
    candidate: EngagementCandidateDTO
    session_id: str | None = None


class DraftEmailResponse(EmailDraftResultDTO):
    session_id: str


class EngagementEmailRequest(BaseModel):
    supplier_name: str
    component: str | None = None
    material: str | None = None
    kg_co2e: float | None = None
    share_pct: float | None = None
    email_body: str


class CreateEngagementsRequest(BaseModel):
    product_name: str
    engagements: list[EngagementEmailRequest]


class CreateEngagementsResponse(BaseModel):
    engagement_ids: dict[str, int]


class ParsedResponseDTO(BaseModel):
    response_type: str
    data_provided: str
    issues_identified: list[str]
    completeness_score: str
    raw_llm_output: str = ""

    @classmethod
    def from_domain(cls, parsed: ParsedResponse) -> "ParsedResponseDTO":
        return cls(**parsed.__dict__)


class ParseResponseResultDTO(BaseModel):
    parsed: ParsedResponseDTO | None
    error: str | None = None

    @classmethod
    def from_domain(cls, result: ParseResponseResult) -> "ParseResponseResultDTO":
        return cls(
            parsed=ParsedResponseDTO.from_domain(result.parsed) if result.parsed else None,
            error=result.error,
        )


class RoutingDecisionDTO(BaseModel):
    action: str
    rationale: str
    ghg_protocol_citation: str | None = None

    @classmethod
    def from_domain(cls, decision: RoutingDecision) -> "RoutingDecisionDTO":
        return cls(**decision.__dict__)


class RoutingResultDTO(BaseModel):
    decision: RoutingDecisionDTO | None
    error: str | None = None

    @classmethod
    def from_domain(cls, result: RoutingResult) -> "RoutingResultDTO":
        return cls(
            decision=RoutingDecisionDTO.from_domain(result.decision) if result.decision else None,
            error=result.error,
        )


class RouteResponseRequest(BaseModel):
    engagement_id: int
    supplier_name: str
    response_text: str
    component: str | None = None
    session_id: str | None = None


class RouteResponseResponse(BaseModel):
    parsed: ParseResponseResultDTO
    routing: RoutingResultDTO | None
    engagement_status: str


class AuditEntryDTO(BaseModel):
    log_id: int
    timestamp: str
    event: str
    workflow: str
    model: str | None
    supplier_name: str | None
    product_name: str | None
    component_name: str | None
    email_sent: str | None
    response_received: str | None
    routing_decision: str | None
    decision_rationale: str | None
    ghg_protocol_citation: str | None
    data_collected: str | None
    status: str | None

    @classmethod
    def from_domain(cls, entry: Any) -> "AuditEntryDTO":
        return cls(**entry.__dict__)
