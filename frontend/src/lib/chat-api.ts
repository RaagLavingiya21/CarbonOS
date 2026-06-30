import { createSupabaseBrowserClient, hasSupabaseConfig } from "@/lib/supabase";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type ChatRole = "user" | "assistant" | "system";

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
  metadata: Record<string, unknown>;
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
  module_launch: Record<string, unknown> | null;
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

export const chatApi = {
  createThread,
  listThreads,
  getThread,
  sendMessage,
};
