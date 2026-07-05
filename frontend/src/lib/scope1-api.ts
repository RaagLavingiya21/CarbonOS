// Isolated API client for the Scope 1 module. Mirrors lib/api.ts's authed
// fetch pattern (Supabase access token -> Bearer) but stays self-contained so
// the Scope 1 surface does not couple to the Carbon OS client.

import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

async function accessToken(): Promise<string> {
  if (!hasSupabaseConfig()) {
    throw new Error("Supabase Auth is not configured.");
  }
  const supabase = createSupabaseBrowserClient();
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  const token = data.session?.access_token;
  if (!token) throw new Error("You must be signed in to continue.");
  return token;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${await accessToken()}`);
  const response = await fetch(`${BACKEND_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

// --- Types ------------------------------------------------------------------

export type S1Entity = {
  id: string;
  name: string;
  jurisdiction: string;
  entity_type: string;
  equity_pct?: number | null;
  economic_interest_pct?: number | null;
  has_financial_control?: boolean;
  has_operational_control?: boolean;
};

export type S1Facility = {
  id: string;
  entity_id: string;
  name: string;
  city?: string | null;
  country?: string | null;
};

export type S1Inventory = {
  id: string;
  reporting_entity_id: string;
  reporting_year: number;
  period_start: string;
  period_end: string;
  consolidation_approach: string;
  base_year: number;
  status: string;
  locked: boolean;
};

export type S1Source = {
  id: string;
  entity_id: string;
  facility_id?: string | null;
  source_name: string;
  source_category: string;
  primary_fuel?: string | null;
  is_excluded?: boolean;
};

export type S1Record = {
  id: string;
  kg_co2_fossil?: number | null;
  kg_co2_biogenic?: number | null;
  kg_ch4?: number | null;
  kg_n2o?: number | null;
  biogenic_fossil_tag?: string;
  data_quality_tier?: number;
  ef_source?: string;
  ef_tier?: string;
};

export type S1ConsolidationPreview = { multiplier: number; rationale: string };

export type S1Readiness = {
  total: number;
  complete: number;
  completeness_pct: number;
  by_status: Record<string, number>;
  items: Array<Record<string, unknown>>;
};

export type S1GasBreakdown = {
  co2_fossil_tco2e: number;
  ch4_tco2e: number;
  n2o_tco2e: number;
  sf6_tco2e: number;
  nf3_tco2e: number;
  total_tco2e: number;
};

export type S1Report = {
  ar_version: string;
  total_scope1_tco2e: number;
  biogenic_co2_tco2e: number;
  by_gas: S1GasBreakdown;
  by_facility: Array<{ facility_id: string | null; facility_name: string | null; tco2e: number }>;
  record_count: number;
};

export type S1Trace = {
  record_id: string;
  ar_version: string;
  consolidation_multiplier: number;
  gases: Array<{ gas: string; kg: number; gwp_100: number; tco2e: number }>;
  total_tco2e: number;
  biogenic_co2_kg: number;
  biogenic_co2_tco2e: number;
  ef_source?: string | null;
  ef_tier?: string | null;
  evidence_document_id?: string | null;
};

export type S1DataOwner = {
  id: string;
  name: string;
  email?: string | null;
  role_title?: string | null;
  owner_type?: string;
};

export type S1CollectionStatus = {
  emission_source_id: string;
  status: string;
  data_owner_id?: string | null;
  period_start?: string;
  period_end?: string;
  notes?: string | null;
};

export type S1Evidence = {
  id: string;
  file_name?: string | null;
  hash_sha256: string;
  storage_uri?: string;
  byte_size?: number | null;
};

export type S1AuditEntry = {
  action: string;
  entity_table?: string;
  entity_id?: string;
  created_at?: string;
  actor_id?: string | null;
};

export type S1CsvResult = {
  created: number;
  record_ids: string[];
  row_errors: Array<{ row: number; errors: string[] }>;
  file_errors: string[];
};

export type S1OcrField = { value: string | null; confidence: number };

export type S1OcrExtraction = {
  id: string;
  inventory_id: string | null;
  evidence_document_id: string | null;
  doc_kind: string;
  extracted: Record<string, S1OcrField>;
  min_confidence: number | null;
  status: string;
  needs_review?: boolean;
};

// --- Client -----------------------------------------------------------------

export const scope1Api = {
  listEntities: () => request<S1Entity[]>("/api/scope1/entities"),
  createEntity: (body: Record<string, unknown>) =>
    request<S1Entity>("/api/scope1/entities", { method: "POST", body: JSON.stringify(body) }),

  listFacilities: () => request<S1Facility[]>("/api/scope1/facilities"),
  createFacility: (body: Record<string, unknown>) =>
    request<S1Facility>("/api/scope1/facilities", { method: "POST", body: JSON.stringify(body) }),

  listDataOwners: () => request<S1DataOwner[]>("/api/scope1/data-owners"),
  createDataOwner: (body: Record<string, unknown>) =>
    request<S1DataOwner>("/api/scope1/data-owners", { method: "POST", body: JSON.stringify(body) }),
  assignOwner: (sourceId: string, dataOwnerId: string) =>
    request<Record<string, unknown>>(`/api/scope1/sources/${sourceId}/assign-owner`, {
      method: "POST",
      body: JSON.stringify({ data_owner_id: dataOwnerId }),
    }),
  initCollection: (inventoryId: string) =>
    request<S1CollectionStatus[]>(`/api/scope1/inventories/${inventoryId}/collection/init`, {
      method: "POST",
    }),
  setCollectionStatus: (body: Record<string, unknown>) =>
    request<S1CollectionStatus>("/api/scope1/collection/status", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listInventories: () => request<S1Inventory[]>("/api/scope1/inventories"),
  createInventory: (body: Record<string, unknown>) =>
    request<S1Inventory>("/api/scope1/inventories", { method: "POST", body: JSON.stringify(body) }),
  lockInventory: (id: string) =>
    request<S1Inventory>(`/api/scope1/inventories/${id}/lock`, { method: "POST" }),

  consolidationPreview: (body: Record<string, unknown>) =>
    request<S1ConsolidationPreview>("/api/scope1/consolidation/preview", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  upsertBoundary: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/scope1/boundary", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  listSources: () => request<S1Source[]>("/api/scope1/sources"),
  createSource: (body: Record<string, unknown>) =>
    request<S1Source>("/api/scope1/sources", { method: "POST", body: JSON.stringify(body) }),

  createStationaryRecord: (body: Record<string, unknown>) =>
    request<S1Record>("/api/scope1/records/stationary", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  createMobileRecord: (body: Record<string, unknown>) =>
    request<S1Record>("/api/scope1/records/mobile", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  uploadEvidence: async (
    file: File,
    inventoryId: string | null,
    documentType = "utility_invoice",
  ): Promise<S1Evidence> => {
    const form = new FormData();
    form.append("file", file);
    if (inventoryId) form.append("inventory_id", inventoryId);
    form.append("document_type", documentType);
    const response = await fetch(`${BACKEND_URL}/api/scope1/evidence`, {
      method: "POST",
      headers: { Authorization: `Bearer ${await accessToken()}` }, // no Content-Type: browser sets multipart boundary
      body: form,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
    }
    return response.json() as Promise<S1Evidence>;
  },

  uploadRecordsCsv: async (inventoryId: string, file: File): Promise<S1CsvResult> => {
    const form = new FormData();
    form.append("inventory_id", inventoryId);
    form.append("file", file);
    const response = await fetch(`${BACKEND_URL}/api/scope1/records/csv`, {
      method: "POST",
      headers: { Authorization: `Bearer ${await accessToken()}` },
      body: form,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
    }
    return response.json() as Promise<S1CsvResult>;
  },

  ocrExtract: async (
    file: File,
    docKind: string,
    inventoryId: string,
  ): Promise<S1OcrExtraction> => {
    const form = new FormData();
    form.append("file", file);
    form.append("doc_kind", docKind);
    form.append("inventory_id", inventoryId);
    const response = await fetch(`${BACKEND_URL}/api/scope1/ocr/extract`, {
      method: "POST",
      headers: { Authorization: `Bearer ${await accessToken()}` },
      body: form,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail ?? `Request failed with ${response.status}`);
    }
    return response.json() as Promise<S1OcrExtraction>;
  },
  ocrQueue: (status = "pending_review") =>
    request<S1OcrExtraction[]>(`/api/scope1/ocr/queue?status=${status}`),
  ocrReview: (extractionId: string, body: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/api/scope1/ocr/${extractionId}/review`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  readiness: (inventoryId: string) =>
    request<S1Readiness>(`/api/scope1/inventories/${inventoryId}/readiness`),
  report: (inventoryId: string, arVersion = "AR5") =>
    request<S1Report>(`/api/scope1/inventories/${inventoryId}/report?ar_version=${arVersion}`),
  recordTrace: (recordId: string, arVersion = "AR5") =>
    request<S1Trace>(`/api/scope1/records/${recordId}/trace?ar_version=${arVersion}`),
  recordAudit: (recordId: string) =>
    request<S1AuditEntry[]>(`/api/scope1/records/${recordId}/audit`),
};
