import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type ChatRole = "user" | "assistant" | "system";

export type ModuleType =
  | "bom_analyzer"
  | "gap_analyzer"
  | "supplier_copilot"
  | "advisor";

export interface IntakeFormField {
  name: string;
  label: string;
  type: string;
  required?: boolean;
  placeholder?: string;
  accept?: string;
  options?: string[];
  default?: number | string;
  min?: number;
  max?: number;
  source?: string;
}

export interface IntakeForm {
  module_type: ModuleType;
  title: string;
  description: string;
  fields: IntakeFormField[];
}

export interface ModuleLaunch {
  module_type: ModuleType;
  step: "intake" | string;
  intake_form?: IntakeForm;
}

export interface ChatMessageMetadata {
  suggestions?: string[];
  module_launch?: ModuleLaunch;
  skill?: string;
  [key: string]: unknown;
}

export interface BomIntakePayload {
  module_type: "bom_analyzer";
  product_name: string;
  file: File;
}

export interface GapAnalyzerIntakePayload {
  module_type: "gap_analyzer";
  company_name: string;
  size: string;
  sector: string;
  geography: string;
  products: string;
}

export interface SupplierCopilotIntakePayload {
  module_type: "supplier_copilot";
  product_id: number;
  product_name: string;
  top_n: number;
}

export type IntakeSubmitPayload =
  | BomIntakePayload
  | GapAnalyzerIntakePayload
  | SupplierCopilotIntakePayload;

export interface ChatThread {
  thread_id: string;
  user_id: string;
  org_id: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface ChatMessage {
  message_id: string;
  thread_id: string;
  role: ChatRole;
  content: string;
  metadata: ChatMessageMetadata;
  created_at: string;
}

export interface ThreadDetail {
  thread: ChatThread;
  messages: ChatMessage[];
}

export interface SendMessageResult {
  thread_id: string;
  content: string;
  suggestions: string[];
  module_launch: ModuleLaunch | null;
}

export function formatIntakeSubmitMessage(payload: IntakeSubmitPayload): string {
  switch (payload.module_type) {
    case "bom_analyzer":
      return `Submitted BOM Analyzer intake: product "${payload.product_name}", file ${payload.file.name}`;
    case "gap_analyzer":
      return (
        `Submitted Gap Analyzer intake: ${payload.company_name} ` +
        `(${payload.size}, ${payload.sector}, ${payload.geography})`
      );
    case "supplier_copilot":
      return (
        `Submitted Supplier Copilot intake: product "${payload.product_name}", ` +
        `top ${payload.top_n} suppliers`
      );
    default:
      return "Submitted module intake form";
  }
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
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = await getAccessToken();
  if (!token) {
    throw new Error("You must be signed in to continue.");
  }
  headers.set("Authorization", `Bearer ${token}`);

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

export async function createThread(
  title?: string,
  orgId?: string,
): Promise<ChatThread> {
  return request<ChatThread>("/api/chat/threads", {
    method: "POST",
    body: JSON.stringify({ title: title ?? null, org_id: orgId ?? null }),
  });
}

export async function listThreads(): Promise<ChatThread[]> {
  return request<ChatThread[]>("/api/chat/threads");
}

export async function getThread(threadId: string): Promise<ThreadDetail> {
  return request<ThreadDetail>(`/api/chat/threads/${threadId}`);
}

export async function sendMessage(
  threadId: string,
  content: string,
): Promise<SendMessageResult> {
  return request<SendMessageResult>(
    `/api/chat/threads/${threadId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
  );
}

export async function deleteThread(threadId: string): Promise<void> {
  await request<{ deleted: boolean }>(`/api/chat/threads/${threadId}`, {
    method: "DELETE",
  });
}

export interface ActivePanel {
  panel_id: string;
  user_id: string;
  thread_id: string | null;
  module_type: ModuleType;
  panel_state: Record<string, unknown>;
  tab_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreatePanelRequest {
  module_type: ModuleType;
  thread_id?: string | null;
  panel_state?: Record<string, unknown>;
  tab_order?: number;
  is_active?: boolean;
}

export interface UpdatePanelRequest {
  panel_state?: Record<string, unknown>;
  tab_order?: number;
  is_active?: boolean;
}

export async function listPanels(): Promise<ActivePanel[]> {
  return request<ActivePanel[]>("/api/panels");
}

export async function createPanel(
  body: CreatePanelRequest,
): Promise<ActivePanel> {
  return request<ActivePanel>("/api/panels", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updatePanel(
  panelId: string,
  body: UpdatePanelRequest,
): Promise<ActivePanel> {
  return request<ActivePanel>(`/api/panels/${panelId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deletePanel(
  panelId: string,
): Promise<{ deleted: boolean }> {
  return request<{ deleted: boolean }>(`/api/panels/${panelId}`, {
    method: "DELETE",
  });
}

export const chatApi = {
  createThread,
  listThreads,
  getThread,
  sendMessage,
  deleteThread,
  listPanels,
  createPanel,
  updatePanel,
  deletePanel,
};
