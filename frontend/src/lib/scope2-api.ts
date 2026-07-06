import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

// Scope 2 ("Grid") API client. Isolated from lib/api.ts: it shares only the
// backend base URL and the Supabase bearer-token pattern, no domain types.
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type Scope2Health = { status: string; module: string };

export type SiteTemplate = {
  site_type: string;
  label: string;
  energy_carriers: string[];
  default_ownership: string;
  default_lease_type: string;
  notes: string;
  typical_utilities: string[];
};

export type Site = {
  site_id: number;
  name: string;
  site_type: string;
  address: string | null;
  zip: string | null;
  country: string | null;
  egrid_subregion: string | null;
  iea_country: string | null;
  ownership: string | null;
  lease_type: string | null;
  franchise_flag: boolean;
  consolidation_approach: string | null;
  status: string | null;
};

export type CreateSitePayload = {
  name: string;
  site_type: string;
  address?: string;
  zip?: string;
  country?: string;
  egrid_subregion?: string;
  ownership?: string;
  lease_type?: string;
  franchise_flag?: boolean;
};

export type EgridSubregion = { code: string; name: string };

export type CsvBillPreview = {
  site_ref: string;
  period_start: string;
  period_end: string;
  canonical_mwh: number | null;
  cost_usd: number | null;
  is_cost_only: boolean;
  is_estimated_read: boolean;
  conversion_note: string | null;
};

export type CsvPreview = {
  total_rows: number;
  valid_count: number;
  error_count: number;
  bills: CsvBillPreview[];
  errors: { row_index: number; message: string }[];
};

export type CsvCommit = {
  total_rows: number;
  committed_count: number;
  error_count: number;
  unresolved_site_refs: string[];
};

export type Calculation = {
  calc_id: number;
  reporting_year: number;
  scope: string;
  site_id: number | null;
  location_based_kg_co2e: number;
  market_based_kg_co2e: number;
  consumption_mwh: number | null;
  market_tier: string | null;
  market_fallback_flagged: boolean;
  created_at: string | null;
};

export type RunCalculationResult = {
  calc_id: number;
  reporting_year: number;
  location_based_kg_co2e: number;
  market_based_kg_co2e: number;
  consumption_mwh: number;
  site_count: number;
  market_fallback_site_count: number;
};

export type LandlordRequest = {
  request_id: number;
  site_id: number;
  site_name: string | null;
  landlord_contact: string | null;
  method: string;
  status: string;
  sent_at: string | null;
  responded_at: string | null;
  reminder_cadence_days: number;
  returned_data_ref: string | null;
  notes: string | null;
  created_at: string | null;
};

export type CreateLandlordPayload = {
  site_id: number;
  landlord_contact?: string;
  method?: string;
  reminder_cadence_days?: number;
  notes?: string;
};

export type EstimateResult = {
  site_id: number;
  reporting_year: number;
  annual_mwh: number;
  intensity_kwh_per_sqft: number;
  method_note: string;
};

export type Coverage = {
  total_mwh: number;
  coverage_fraction: number;
  estimation_fraction: number;
  site_count: number;
  sites_with_data: number;
  sites_missing_data: number;
  per_site: {
    site_id: number;
    total_mwh: number;
    coverage_fraction: number;
    has_data: boolean;
  }[];
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
    throw new Error(`Scope 2 API ${response.status}: ${detail}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const scope2Api = {
  health: () => request<Scope2Health>("/api/scope2/health"),
  siteTemplates: () => request<SiteTemplate[]>("/api/scope2/site-templates"),

  egridSubregions: () =>
    request<EgridSubregion[]>("/api/scope2/egrid-subregions"),

  listSites: () => request<Site[]>("/api/scope2/sites"),
  createSite: (payload: CreateSitePayload) =>
    request<Site>("/api/scope2/sites", { method: "POST", body: payload }),
  deleteSite: (siteId: number) =>
    request<void>(`/api/scope2/sites/${siteId}`, { method: "DELETE" }),

  previewCsv: (csvText: string, mapping: Record<string, string>) =>
    request<CsvPreview>("/api/scope2/bills/preview-csv", {
      method: "POST",
      body: { csv_text: csvText, mapping },
    }),
  commitCsv: (csvText: string, mapping: Record<string, string>) =>
    request<CsvCommit>("/api/scope2/bills/import-csv", {
      method: "POST",
      body: { csv_text: csvText, mapping },
    }),

  runCalculation: (reportingYear: number) =>
    request<RunCalculationResult>("/api/scope2/calculations", {
      method: "POST",
      body: { reporting_year: reportingYear },
    }),
  listCalculations: () => request<Calculation[]>("/api/scope2/calculations"),
  coverage: () => request<Coverage>("/api/scope2/coverage"),

  listLandlordRequests: () =>
    request<LandlordRequest[]>("/api/scope2/landlord-requests"),
  createLandlordRequest: (payload: CreateLandlordPayload) =>
    request<LandlordRequest>("/api/scope2/landlord-requests", {
      method: "POST",
      body: payload,
    }),
  updateLandlordRequest: (requestId: number, updates: Record<string, unknown>) =>
    request<LandlordRequest>(`/api/scope2/landlord-requests/${requestId}`, {
      method: "PATCH",
      body: updates,
    }),
  deleteLandlordRequest: (requestId: number) =>
    request<void>(`/api/scope2/landlord-requests/${requestId}`, {
      method: "DELETE",
    }),

  estimateSite: (siteId: number, floorAreaSqft: number, reportingYear: number) =>
    request<EstimateResult>(`/api/scope2/sites/${siteId}/estimate`, {
      method: "POST",
      body: { floor_area_sqft: floorAreaSqft, reporting_year: reportingYear },
    }),
};
