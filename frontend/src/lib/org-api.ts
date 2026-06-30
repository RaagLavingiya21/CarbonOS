import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export interface Organization {
  id: string;
  name: string;
  created_at: string;
  is_demo: boolean;
}

export interface OrgMember {
  user_id: string;
  org_id: string;
  role: string;
}

export interface OrgDetail {
  orgs: Organization[];
  active_org: Organization | null;
  members: OrgMember[];
}

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
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = await getAccessToken();
  if (!token) {
    throw new Error("You must be signed in to continue.");
  }
  headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      `Could not reach the API at ${BACKEND_URL}. Is the backend running?`,
    );
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg ?? JSON.stringify(item)).join("; ")
          : `Request failed with ${response.status}`;
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function getMyOrg(): Promise<OrgDetail> {
  return request<OrgDetail>("/api/orgs/mine");
}

export async function createOrg(name: string): Promise<Organization> {
  return request<Organization>("/api/orgs", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function setActiveOrg(orgId: string): Promise<Organization> {
  return request<Organization>("/api/orgs/active", {
    method: "PATCH",
    body: JSON.stringify({ org_id: orgId }),
  });
}

export async function addMember(orgId: string, email: string): Promise<OrgMember> {
  return request<OrgMember>(`/api/orgs/${orgId}/members`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function removeMember(
  orgId: string,
  userId: string,
): Promise<{ removed: boolean }> {
  return request<{ removed: boolean }>(`/api/orgs/${orgId}/members/${userId}`, {
    method: "DELETE",
  });
}

export function workspaceLabel(org: Organization): string {
  return org.is_demo ? `Demo — ${org.name}` : `Your workspace — ${org.name}`;
}

export const orgApi = {
  getMyOrg,
  createOrg,
  setActiveOrg,
  addMember,
  removeMember,
  workspaceLabel,
};
