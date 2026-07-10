import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

// Scope 3 API client. Isolated from lib/api.ts and lib/scope2-api.ts: it shares
// only the backend base URL and the Supabase bearer-token pattern. Backend
// routes live under /scope-3 and ship dark behind NEXT_PUBLIC_SCOPE3_ENABLED.
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export type InventoryVersion = {
  inventory_id: number;
  org_id: string;
  reporting_year: number;
  boundary_approach: string;
  status: string;
  is_base_year: boolean;
  total_kg_co2e: number | null;
  version: number;
  created_at: string | null;
  locked_at: string | null;
};

export type CategoryResult = {
  scope3_category: number;
  method: string;
  total_kg_co2e: number;
  line_count: number;
  notes: string | null;
};

export type InventoryDetail = {
  version: InventoryVersion;
  categories: CategoryResult[];
};

export type CreateInventoryPayload = {
  reporting_year: number;
  boundary_approach: string;
};

export type SpendImportResult = {
  inventory_id: number;
  parsed_rows: number;
  flagged_rows: number;
  file_errors: string[];
};

export const BOUNDARY_APPROACHES = [
  "operational_control",
  "financial_control",
  "equity",
] as const;

// --- Epic C: obligation front door -----------------------------------------

export type CompanyProfile = {
  annual_revenue_usd: number | null;
  employee_count: number | null;
  is_us_entity: boolean;
  does_business_in_ca: boolean;
  eu_turnover_eur: number | null;
  eu_subsidiary: boolean;
  eu_branch_turnover_eur: number | null;
  listed_jurisdictions: string[];
  sector: string;
  is_flag_sector: boolean;
  key_customers: string[];
};

export type ObligationDue = {
  what: string;
  date: string | null;
  note: string | null;
};

export type Obligation = {
  rule_id: string;
  framework: string;
  applies: string;
  reason: string;
  threshold_detail: string;
  confidence: string;
  status: string;
  due: ObligationDue[];
  assurance: string | null;
  citation: string;
  priority: number;
};

export type TimelineItem = {
  date: string;
  framework: string;
  what: string;
};

export type CascadeSignal = {
  customer: string;
  matched_buyer: string;
  regimes: string[];
  rationale: string;
};

export type BusinessCase = {
  headline: string;
  primary_driver: string | null;
  applicable_count: number;
  uncertain_count: number;
  at_stake: string[];
  watch_items: string[];
  cascade_exposure: string[];
};

export type ObligationEvaluation = {
  ruleset_version: string;
  applicable: Obligation[];
  uncertain: Obligation[];
  not_applicable: Obligation[];
  timeline: TimelineItem[];
  business_case: BusinessCase;
  cascade: CascadeSignal[];
};

// --- Epic B: inbound request -> questionnaire answer -----------------------

export type QuestionnaireRequest = {
  request_id: number;
  org_id: string;
  customer_name: string | null;
  framework: string;
  status: string;
  deadline: string | null;
  inventory_id: number | null;
  created_at: string | null;
};

export type CreateQuestionnairePayload = {
  customer_name: string | null;
  framework: string | null;
  deadline: string | null;
  inventory_id: number | null;
};

export type DetectResult = {
  request_id: number;
  framework: string;
  is_low_confidence: boolean;
  question_count: number;
};

export type MapResult = {
  request_id: number;
  mapped: number;
  needs_human: number;
};

export type Question = {
  question_id: number;
  question_index: number;
  question_text: string;
  question_type: string;
  framework_field_key: string | null;
};

export type QuestionMapping = {
  question_id: number;
  datapoint_ref: string | null;
  mapped_value: number | null;
  answer_text: string | null;
  confidence_score: number;
  method: string;
  citation: string | null;
  flag_status: string;
};

export type QuestionnaireDetail = {
  request: QuestionnaireRequest;
  questions: Question[];
  mappings: QuestionMapping[];
};

// --- Epic D: SBTi / FLAG targets -------------------------------------------

export type TargetWizardPayload = {
  inventory_id: number;
  base_year: number;
  target_year: number;
  reduction_pct: number;
  method: string;
  horizon: string;
  version: string;
  covered_categories: number[];
  sector: string;
  flag_kg_co2e: number;
};

export type TrajectoryPoint = { year: number; target_kg_co2e: number };

export type Ambition = {
  chosen_reduction_pct: number;
  reference_reduction_pct: number;
  meets_reference: boolean;
  note: string;
};

export type FlagInfo = {
  is_flag_required: boolean;
  flag_share: number;
  reason: string;
  no_deforestation_commitment_date: string | null;
};

export type DraftTarget = {
  version: string;
  horizon: string;
  category_class: string;
  scope3_target_mandatory: boolean;
  base_year_assurance_required: boolean;
  total_scope3_kg: number;
  required_categories: number[];
  coverage_gap: number[];
  meets_requirement: boolean | null;
  trajectory: TrajectoryPoint[];
  ambition: Ambition;
  flag: FlagInfo | null;
  notes: string[];
};

export type Target = {
  target_id: number;
  org_id: string;
  type: string;
  method: string;
  sbti_version: string;
  base_year: number | null;
  target_year: number | null;
  reduction_pct: number | null;
  inventory_base_id: number | null;
  status: string;
  assurance_required: boolean;
};

// --- Epic E: progress tracking ---------------------------------------------

export type ProgressTrackPayload = {
  base_inventory_id: number;
  current_inventory_id: number;
  target_id: number | null;
  trajectory: Record<string, number>;
};

export type ProgressResult = {
  current_year: number;
  base_total_kg: number;
  real_total_kg: number;
  actual_total_kg: number;
  trajectory_target_kg: number | null;
  on_track: boolean | null;
  method_delta_kg: number;
  notes: string[];
};

export type RecalcPayload = {
  trigger: string;
  significance_pct: number;
  threshold_pct: number | null;
};

export type RecalcResult = {
  trigger: string;
  significance_pct: number;
  threshold_pct: number;
  recalc_required: boolean;
  rationale: string;
};

// --- Epic G: disclosure ----------------------------------------------------

export type DisclosureDatapoint = {
  key: string;
  label: string;
  value: number | null;
  text: string | null;
  unit: string;
  source_ref: string | null;
  flag: string;
};

export type DisclosureResult = {
  framework: string;
  format_version: string;
  is_provisional: boolean;
  datapoints: DisclosureDatapoint[];
  category_breakdown: DisclosureDatapoint[];
  notes: string[];
};

// --- Epic F: suppliers -----------------------------------------------------

export type SupplierCreatePayload = {
  name: string;
  scope3_category: number;
  emissions_kg: number;
  spend_usd: number;
  pcf_received: boolean;
  dq_score: number | null;
  supplier_sbt_status: string;
};

export type Supplier = {
  supplier_id: number;
  org_id: string;
  name: string;
  scope3_category: number;
  emissions_kg: number;
  spend_usd: number;
  pcf_received: boolean;
  dq_score: number | null;
  supplier_sbt_status: string;
};

export type CohortPayload = {
  hotspot_categories: number[];
  top_n: number;
  basis: string;
};

export type Cohort = {
  basis: string;
  hotspot_categories: number[];
  emissions_covered_pct: number;
  members: Supplier[];
};

export type SupplierScorecard = {
  supplier_count: number;
  pcf_coverage_pct: number;
  emissions_covered_pct: number;
  avg_dq: number | null;
  sbt_committed_count: number;
  sbt_validated_count: number;
};

// --- Epic H: use-phase (Category 11) ---------------------------------------

export type UsePhasePayload = {
  product_ref: string;
  energy_per_use_kwh: number;
  water_l_per_use: number;
  standby_power_w: number;
  fuel_kwh_per_use: number;
  uses_per_year: number;
  lifetime_years: number;
  units_sold: number;
  region: string | null;
  mode: string;
  include_standby: boolean;
};

export type UsePhaseResult = {
  product_name: string;
  units_sold: number;
  kg_co2e: number;
  direct_or_indirect: string;
  method: string;
  ef_source: string;
  dq_note: string;
  breakdown: Record<string, number>;
};

// --- Epic I: levers / MAC / claims -----------------------------------------

export type Lever = {
  lever_id: string;
  name: string;
  category: number;
  abatement_pct: number;
  cost_per_tco2e: number;
  applicability: string[];
  source: string;
};

export type MacPoint = {
  lever_id: string;
  name: string;
  category: number;
  abatement_tco2e: number;
  cost_per_tco2e: number;
  cumulative_abatement_tco2e: number;
};

export type ComplianceFlag = {
  rule_id: string;
  jurisdiction: string;
  framework: string;
  verdict: string;
  note: string;
};

export type ClaimAssessment = {
  claim_text: string;
  jurisdiction: string;
  substantiable: boolean;
  substantiation_reason: string;
  ruleset_version: string;
  flags: ComplianceFlag[];
};

export type ClaimAssessPayload = {
  claim_text: string;
  primary_data_share: number;
  assured: boolean;
  jurisdiction: string;
  offset_based: boolean;
};

async function getAccessToken(): Promise<string | null> {
  if (!hasSupabaseConfig()) return null;
  const supabase = createSupabaseBrowserClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const token = await getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json())?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`Scope 3 API ${response.status}: ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function upload<T>(path: string, file: File): Promise<T> {
  const headers = new Headers();
  const token = await getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers,
    body: form,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json())?.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`Scope 3 API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const scope3Api = {
  listInventories: () => request<InventoryVersion[]>("/scope-3/inventory"),
  createInventory: (payload: CreateInventoryPayload) =>
    request<InventoryVersion>("/scope-3/inventory", { method: "POST", body: payload }),
  getInventory: (id: number) => request<InventoryDetail>(`/scope-3/inventory/${id}`),
  importSpend: (id: number, file: File) =>
    upload<SpendImportResult>(`/scope-3/inventory/${id}/spend/import`, file),
  calculate: (id: number) =>
    request<InventoryDetail>(`/scope-3/inventory/${id}/calculate`, { method: "POST" }),
  lock: (id: number) =>
    request<InventoryVersion>(`/scope-3/inventory/${id}/lock`, { method: "POST" }),

  // Epic C: obligation front door
  getCompanyProfile: () =>
    request<CompanyProfile | null>("/scope-3/company-profile"),
  saveCompanyProfile: (payload: CompanyProfile) =>
    request<CompanyProfile>("/scope-3/company-profile", { method: "POST", body: payload }),
  evaluateObligations: () =>
    request<ObligationEvaluation>("/scope-3/obligations/evaluate", { method: "POST" }),
  listObligations: () => request<Obligation[]>("/scope-3/obligations"),

  // Epic B: inbound request -> questionnaire answer
  listQuestionnaires: () =>
    request<QuestionnaireRequest[]>("/scope-3/questionnaires"),
  createQuestionnaire: (payload: CreateQuestionnairePayload) =>
    request<QuestionnaireRequest>("/scope-3/questionnaires", {
      method: "POST",
      body: payload,
    }),
  getQuestionnaire: (id: number) =>
    request<QuestionnaireDetail>(`/scope-3/questionnaires/${id}`),
  detectQuestionnaire: (id: number, file: File) =>
    upload<DetectResult>(`/scope-3/questionnaires/${id}/detect`, file),
  mapQuestionnaire: (id: number) =>
    request<MapResult>(`/scope-3/questionnaires/${id}/map`, { method: "POST" }),
  submitQuestionnaire: (id: number) =>
    request<QuestionnaireRequest>(`/scope-3/questionnaires/${id}/submit`, {
      method: "POST",
    }),
  exportQuestionnaire: async (id: number, format: "csv" | "markdown") => {
    const headers = new Headers();
    const token = await getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(
      `${BACKEND_URL}/scope-3/questionnaires/${id}/export?format=${format}`,
      { method: "POST", headers },
    );
    if (!response.ok) {
      let detail = response.statusText;
      try {
        detail = (await response.json())?.detail ?? detail;
      } catch {
        /* non-JSON error body */
      }
      throw new Error(`Scope 3 API ${response.status}: ${detail}`);
    }
    return response.blob();
  },

  // Epic D: SBTi / FLAG targets
  targetWizard: (payload: TargetWizardPayload) =>
    request<DraftTarget>("/scope-3/targets/wizard", { method: "POST", body: payload }),
  createTarget: (payload: TargetWizardPayload) =>
    request<Target>("/scope-3/targets", { method: "POST", body: payload }),
  listTargets: () => request<Target[]>("/scope-3/targets"),

  // Epic E: progress tracking
  trackProgress: (payload: ProgressTrackPayload) =>
    request<ProgressResult>("/scope-3/progress/track", { method: "POST", body: payload }),
  listProgress: () => request<Record<string, unknown>[]>("/scope-3/progress"),
  recalcCheck: (payload: RecalcPayload) =>
    request<RecalcResult>("/scope-3/progress/recalc", { method: "POST", body: payload }),

  // Epic G: disclosure
  listFrameworks: () => request<string[]>("/scope-3/disclosures/frameworks"),
  calculateDisclosure: (inventoryId: number, framework: string) =>
    request<DisclosureResult>("/scope-3/disclosures/calculate", {
      method: "POST",
      body: { inventory_id: inventoryId, framework },
    }),
  exportDisclosure: async (
    inventoryId: number,
    framework: string,
    format: "csv" | "markdown",
  ) => {
    const headers = new Headers();
    const token = await getAccessToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(
      `${BACKEND_URL}/scope-3/disclosures/export?inventory_id=${inventoryId}&framework=${encodeURIComponent(
        framework,
      )}&format=${format}`,
      { method: "GET", headers },
    );
    if (!response.ok) {
      let detail = response.statusText;
      try {
        detail = (await response.json())?.detail ?? detail;
      } catch {
        /* non-JSON error body */
      }
      throw new Error(`Scope 3 API ${response.status}: ${detail}`);
    }
    return response.blob();
  },

  // Epic F: suppliers
  listSuppliers: () => request<Supplier[]>("/scope-3/suppliers"),
  createSupplier: (payload: SupplierCreatePayload) =>
    request<Supplier>("/scope-3/suppliers", { method: "POST", body: payload }),
  deleteSupplier: (id: number) =>
    request<void>(`/scope-3/suppliers/${id}`, { method: "DELETE" }),
  supplierCohort: (payload: CohortPayload) =>
    request<Cohort>("/scope-3/suppliers/cohort", { method: "POST", body: payload }),
  supplierScorecard: () =>
    request<SupplierScorecard>("/scope-3/suppliers/scorecard"),

  // Epic H: use-phase
  usePhaseSubSectors: () => request<string[]>("/scope-3/use-phase/sub-sectors"),
  calcUsePhase: (payload: UsePhasePayload) =>
    request<UsePhaseResult>("/scope-3/use-phase/calc", { method: "POST", body: payload }),
  listSpecs: () => request<Record<string, unknown>[]>("/scope-3/use-phase/specs"),
  createSpec: (payload: UsePhasePayload) =>
    request<Record<string, unknown>>("/scope-3/use-phase/specs", {
      method: "POST",
      body: payload,
    }),
  deleteSpec: (id: number) =>
    request<void>(`/scope-3/use-phase/specs/${id}`, { method: "DELETE" }),

  // Epic I: levers / MAC / claims
  listLevers: (categories: number[], subSector?: string) =>
    request<Lever[]>(
      `/scope-3/levers?categories=${categories.join(",")}` +
        (subSector ? `&sub_sector=${encodeURIComponent(subSector)}` : ""),
    ),
  buildMac: (categoryTotalsTco2e: Record<string, number>, subSector?: string) =>
    request<MacPoint[]>("/scope-3/mac", {
      method: "POST",
      body: { category_totals_tco2e: categoryTotalsTco2e, sub_sector: subSector ?? null },
    }),
  assessClaim: (payload: ClaimAssessPayload) =>
    request<ClaimAssessment>("/scope-3/claims/assess", { method: "POST", body: payload }),
  listClaims: () => request<Record<string, unknown>[]>("/scope-3/claims"),
};

export const SCOPE3_CATEGORY_NAMES: Record<number, string> = {
  1: "Purchased goods & services",
  2: "Capital goods",
  3: "Fuel- & energy-related",
  4: "Upstream transportation",
  5: "Waste in operations",
  6: "Business travel",
  7: "Employee commuting",
  8: "Upstream leased assets",
  9: "Downstream transportation",
  10: "Processing of sold products",
  11: "Use of sold products",
  12: "End-of-life treatment",
  13: "Downstream leased assets",
  14: "Franchises",
  15: "Investments",
};
