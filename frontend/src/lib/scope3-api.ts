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
