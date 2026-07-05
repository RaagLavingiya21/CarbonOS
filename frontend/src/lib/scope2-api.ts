import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

// Scope 2 ("Grid") API client. Isolated from lib/api.ts: it shares only the
// backend base URL and the Supabase bearer-token pattern, no domain types.
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type Scope2Health = {
  status: string;
  module: string;
};

export type SiteTemplate = {
  site_type: string;
  label: string;
  energy_carriers: string[];
  default_ownership: string;
  default_lease_type: string;
  notes: string;
  typical_utilities: string[];
};

async function getAccessToken(): Promise<string | null> {
  if (!hasSupabaseConfig()) return null;
  const supabase = createSupabaseBrowserClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

async function request<T>(path: string): Promise<T> {
  const headers = new Headers({ "Content-Type": "application/json" });
  const token = await getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${BACKEND_URL}${path}`, { headers });
  if (!response.ok) {
    const detail = await response.text().catch(() => response.statusText);
    throw new Error(`Scope 2 API ${response.status}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const scope2Api = {
  health: () => request<Scope2Health>("/api/scope2/health"),
  siteTemplates: () => request<SiteTemplate[]>("/api/scope2/site-templates"),
};
