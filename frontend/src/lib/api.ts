import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type AnalysisSummary = {
  product_id: number;
  product_name: string;
  analysis_date: string;
  total_kg_co2e: number;
  matched_items: number;
  flagged_items: number;
  status?: string | null;
  flagged_comment?: string | null;
};

export type AnalysisLineItem = {
  component: string | null;
  material: string | null;
  spend_usd: number | null;
  matched_sector: string | null;
  emission_factor: number | null;
  ef_source: string | null;
  kg_co2e: number | null;
  share_pct: number | null;
  flag_status: string;
};

export type AnalysisDetail = AnalysisSummary & {
  line_items: AnalysisLineItem[];
};

export type BomFlag = {
  row_index: number;
  field: string;
  flag_type: string;
  message: string;
  severity: string;
};

export type BomRow = {
  row_index: number;
  component: string | null;
  material: string | null;
  quantity: number | null;
  spend_usd: number | null;
  weight_kg: number | null;
  supplier: string | null;
  country_of_origin: string | null;
  flags: BomFlag[];
};

export type ParsedBom = {
  product_name: string;
  rows: BomRow[];
  file_errors: string[];
  is_valid: boolean;
  flagged_row_indices: number[];
  all_flags: BomFlag[];
};

export type FootprintLineItem = BomRow & {
  sector_name: string;
  sector_code: string;
  ef_kg_co2e_per_usd: number;
  ef_source: string;
  ef_confidence: number;
  kg_co2e: number;
  share_pct: number;
  is_matched: boolean;
  is_low_confidence: boolean;
  is_no_ef_match: boolean;
  is_flagged_by_parser: boolean;
};

export type FootprintResult = {
  product_name: string;
  total_kg_co2e: number;
  line_items: FootprintLineItem[];
  matched_count: number;
  flagged_count: number;
  unmatched_count: number;
  completeness_pct: number;
  has_any_results: boolean;
  hotspots: FootprintLineItem[];
};

export type CriticReport = {
  findings: Array<{
    check: string;
    severity: string;
    message: string;
    row_index: number | null;
  }>;
  total_was_corrected: boolean;
  original_total: number | null;
  has_findings: boolean;
  correction_count: number;
  warning_count: number;
};

export type AnalyzeResponse = {
  session_id: string;
  phase: "calc_review" | "saved";
  bom: ParsedBom;
  warnings: string[];
  result: FootprintResult;
  critic_report: CriticReport;
  product_id: number | null;
};

export type EFMatch = {
  material_input: string;
  sector_name: string;
  sector_code: string;
  ef_kg_co2e_per_usd: number;
  country_used: string;
  confidence_score: number;
  is_low_confidence: boolean;
  is_no_match: boolean;
  source_citation: string;
  suggested_alternatives: string[];
};

export type ParseBOMResponse = {
  session_id: string;
  phase: "bom_review";
  bom: ParsedBom;
};

export type MatchFactorsResponse = {
  session_id: string;
  phase: "ef_review";
  ef_matches: (EFMatch | null)[];
  warnings: string[];
};

export type CalculateFootprintResponse = {
  session_id: string;
  phase: "calc_review";
  result: FootprintResult;
  critic_report: CriticReport;
};

export type Message = {
  role: "user" | "assistant";
  content: string;
};

export type AdvisorChatResponse = {
  session_id: string;
  content: string;
  has_data_reference: boolean;
  citations: string[];
  error: string | null;
};

export type CompanyProfile = {
  name: string;
  size: string;
  sector: string;
  geography: string;
  products: string;
};

export type PlanStep = {
  step_num: number;
  tool_name: string;
  rationale: string;
  has_checkpoint_after: boolean;
};

export type GapPlanResponse = {
  session_id: string;
  phase: "planning";
  profile: CompanyProfile;
  plan: {
    steps: PlanStep[];
    raw_plan_text: string;
  };
  current_step: number;
};

export type ToolResult = {
  tool_name: string;
  content: string;
  structured: Record<string, unknown>;
  citations: string[];
  error: string | null;
};

export type GapExecuteResponse = {
  session_id: string;
  phase: "executing" | "checkpoint" | "done";
  current_step: number;
  result?: ToolResult | null;
  results: Record<string, ToolResult>;
};

export type GapApproveResponse = {
  session_id: string;
  phase: "executing" | "done";
  current_step: number;
};

export type GapReportResponse = {
  session_id: string;
  profile: CompanyProfile;
  markdown: string;
  results: Record<string, ToolResult>;
};

export type EngagementCandidate = {
  supplier_name: string;
  component: string | null;
  material: string | null;
  kg_co2e: number | null;
  share_pct: number | null;
  contact_found: boolean;
  contact_name: string | null;
  contact_email: string | null;
  existing_engagement_id: number | null;
  engagement_status: string;
};

export type SuppliersListResponse = {
  product_name: string;
  candidates: EngagementCandidate[];
  error: string | null;
};

export type EmailDraft = {
  to: string;
  subject: string;
  body: string;
  ghg_protocol_basis: string;
};

export type DraftEmailResponse = {
  session_id: string;
  draft: EmailDraft | null;
  citations: string[];
  error: string | null;
};

export type RouteResponseResponse = {
  parsed: {
    parsed: {
      response_type: string;
      data_provided: string;
      issues_identified: string[];
      completeness_score: string;
      raw_llm_output: string;
    } | null;
    error: string | null;
  };
  routing: {
    decision: {
      action: string;
      rationale: string;
      ghg_protocol_citation: string | null;
    } | null;
    error: string | null;
  } | null;
  engagement_status: string;
};

async function getAccessToken() {
  if (!hasSupabaseConfig()) {
    throw new Error(
      "Supabase Auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.",
    );
  }
  const supabase = createSupabaseBrowserClient();
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session?.access_token;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (authenticated) {
    const token = await getAccessToken();
    if (!token) {
      throw new Error("You must be signed in to continue.");
    }
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BACKEND_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  listAnalyses: () => request<AnalysisSummary[]>("/api/analyses"),
  getAnalysis: (id: string) => request<AnalysisDetail>(`/api/analyses/${id}`),
  exportAnalysisCsv: async (id: string) => {
    const token = await getAccessToken();
    const response = await fetch(`${BACKEND_URL}/api/analyses/${id}/export?format=csv`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? `Export failed with ${response.status}`);
    }
    return response.blob();
  },
  analyzeBom: (file: File, productName?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (productName) formData.append("product_name", productName);
    return request<AnalyzeResponse>("/api/analyze", {
      method: "POST",
      body: formData,
    });
  },
  parseBom: (file: File, productName?: string) => {
    const formData = new FormData();
    formData.append("file", file);
    if (productName) formData.append("product_name", productName);
    return request<ParseBOMResponse>("/api/analyze/parse", {
      method: "POST",
      body: formData,
    });
  },
  matchFactors: (sessionId: string) =>
    request<MatchFactorsResponse>("/api/analyze/match-factors", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),
  calculateFootprint: (sessionId: string) =>
    request<CalculateFootprintResponse>("/api/analyze/calculate", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),
  saveAnalysis: (
    sessionId: string,
    productName: string,
    status: "approved" | "flagged",
    flaggedComment?: string,
  ) =>
    request<{ product_id: number; phase: "saved" }>("/api/analyses", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId,
        product_name: productName,
        status,
        flagged_comment: flaggedComment,
      }),
    }),
  chatAdvisor: (
    userMessage: string,
    conversationHistory: Message[],
    sessionId?: string,
  ) =>
    request<AdvisorChatResponse>("/api/advisor/chat", {
      method: "POST",
      body: JSON.stringify({
        user_message: userMessage,
        conversation_history: conversationHistory,
        session_id: sessionId,
      }),
    }),
  planGapAnalysis: (profile: CompanyProfile) =>
    request<GapPlanResponse>("/api/gap-analysis/plan", {
      method: "POST",
      body: JSON.stringify({ profile }),
    }),
  executeGapStep: (sessionId: string) =>
    request<GapExecuteResponse>("/api/gap-analysis/execute", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),
  approveGapCheckpoint: (sessionId: string, action: "continue" | "stop") =>
    request<GapApproveResponse>("/api/gap-analysis/approve", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, action }),
    }),
  getGapReport: (sessionId: string) =>
    request<GapReportResponse>(`/api/gap-analysis/sessions/${sessionId}/report`),
  listSuppliers: (productName: string, topN = 10) =>
    request<SuppliersListResponse>(
      `/api/copilot/suppliers?product_name=${encodeURIComponent(productName)}&top_n=${topN}`,
    ),
  draftEmail: (
    productName: string,
    candidate: EngagementCandidate,
    sessionId?: string,
  ) =>
    request<DraftEmailResponse>("/api/copilot/draft-email", {
      method: "POST",
      body: JSON.stringify({
        product_name: productName,
        candidate,
        session_id: sessionId,
      }),
    }),
  createEngagement: (
    productName: string,
    candidate: EngagementCandidate,
    emailBody: string,
  ) =>
    request<{ engagement_ids: Record<string, number> }>("/api/copilot/engagements", {
      method: "POST",
      body: JSON.stringify({
        product_name: productName,
        engagements: [
          {
            supplier_name: candidate.supplier_name,
            component: candidate.component,
            material: candidate.material,
            kg_co2e: candidate.kg_co2e,
            share_pct: candidate.share_pct,
            email_body: emailBody,
          },
        ],
      }),
    }),
  routeSupplierResponse: (
    engagementId: number,
    supplierName: string,
    responseText: string,
    component?: string | null,
  ) =>
    request<RouteResponseResponse>("/api/copilot/route-response", {
      method: "POST",
      body: JSON.stringify({
        engagement_id: engagementId,
        supplier_name: supplierName,
        response_text: responseText,
        component,
      }),
    }),
};
