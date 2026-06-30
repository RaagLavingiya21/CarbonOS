"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatThread } from "@/components/chat/ChatThread";
import { ThreadList } from "@/components/chat/ThreadList";
import { SplitLayout } from "@/components/layout/SplitLayout";
import { PanelContainer } from "@/components/panels/PanelContainer";
import {
  PanelProvider,
  usePanels,
} from "@/components/panels/PanelContext";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  chatApi,
  formatIntakeSubmitMessage,
  type ChatMessage,
  type ChatThread as ChatThreadType,
  type IntakeSubmitPayload,
  type ModuleLaunch,
} from "@/lib/chat-api";

function moduleLaunchPanelState(
  moduleLaunch: ModuleLaunch,
): Record<string, unknown> {
  const state: Record<string, unknown> = { step: moduleLaunch.step };
  for (const [key, value] of Object.entries(moduleLaunch)) {
    if (key !== "module_type" && key !== "intake_form") {
      state[key] = value;
    }
  }
  return state;
}

function shouldOpenPanel(moduleLaunch: ModuleLaunch | null): boolean {
  return Boolean(moduleLaunch && moduleLaunch.step !== "intake");
}

function buildIntakePanelState(
  payload: IntakeSubmitPayload,
): Record<string, unknown> {
  switch (payload.module_type) {
    case "bom_analyzer":
      return { step: "parsing", product_name: payload.product_name };
    case "gap_analyzer":
      return {
        step: "planning",
        company_name: payload.company_name,
        size: payload.size,
        sector: payload.sector,
        geography: payload.geography,
        products: payload.products,
      };
    case "supplier_copilot":
      return {
        step: "review",
        product_id: payload.product_id,
        product_name: payload.product_name,
        top_n: payload.top_n,
      };
    default:
      return { step: "review" };
  }
}

function sortThreadsByUpdatedAt(threads: ChatThreadType[]): ChatThreadType[] {
  return [...threads].sort(
    (left, right) =>
      new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  );
}

function ChatWorkspace() {
  const { openPanel } = usePanels();
  const router = useRouter();
  const searchParams = useSearchParams();
  const autoSendHandledRef = useRef(false);
  const [threads, setThreads] = useState<ChatThreadType[]>([]);
  const [thread, setThread] = useState<ChatThreadType | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [switchingThread, setSwitchingThread] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamErrorText, setStreamErrorText] = useState<string | null>(null);
  const [retryText, setRetryText] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(
    null,
  );
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);
  const [submittedIntakeMessageIds, setSubmittedIntakeMessageIds] = useState<
    Set<string>
  >(() => new Set());

  const refreshThreads = useCallback(async () => {
    const listed = await chatApi.listThreads();
    setThreads(sortThreadsByUpdatedAt(listed));
    return sortThreadsByUpdatedAt(listed);
  }, []);

  const selectThread = useCallback(async (threadId: string) => {
    if (thread?.thread_id === threadId) {
      return;
    }

    setSwitchingThread(true);
    setError(null);

    try {
      const detail = await chatApi.getThread(threadId);
      setThread(detail.thread);
      setMessages(detail.messages);
      setSubmittedIntakeMessageIds(new Set());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSwitchingThread(false);
    }
  }, [thread?.thread_id]);

  const startThread = useCallback(async () => {
    setError(null);

    try {
      const created = await chatApi.createThread();
      setThread(created);
      setMessages([]);
      setSubmittedIntakeMessageIds(new Set());
      setThreads((current) =>
        sortThreadsByUpdatedAt([
          created,
          ...current.filter((item) => item.thread_id !== created.thread_id),
        ]),
      );
      return created;
    } catch (err) {
      setThread(null);
      setError((err as Error).message);
      return null;
    }
  }, []);

  const initializeWorkspace = useCallback(async () => {
    setInitializing(true);
    setError(null);

    const messageParam = searchParams.get("message");
    const threadParam = searchParams.get("thread");

    try {
      const listed = await refreshThreads();

      if (messageParam && !autoSendHandledRef.current) {
        autoSendHandledRef.current = true;
        const created = await chatApi.createThread();
        setThread(created);
        setMessages([]);
        setSubmittedIntakeMessageIds(new Set());
        setThreads(
          sortThreadsByUpdatedAt([
            created,
            ...listed.filter((item) => item.thread_id !== created.thread_id),
          ]),
        );
        setPendingMessage(messageParam);
        router.replace("/chat");
      } else if (threadParam) {
        const detail = await chatApi.getThread(threadParam);
        setThread(detail.thread);
        setMessages(detail.messages);
        setSubmittedIntakeMessageIds(new Set());
        router.replace("/chat");
      } else if (listed.length > 0) {
        const detail = await chatApi.getThread(listed[0].thread_id);
        setThread(detail.thread);
        setMessages(detail.messages);
        setSubmittedIntakeMessageIds(new Set());
      } else {
        await startThread();
      }
    } catch (err) {
      setThread(null);
      setError((err as Error).message);
    } finally {
      setInitializing(false);
    }
  }, [refreshThreads, router, searchParams, startThread]);

  useEffect(() => {
    void initializeWorkspace();
    // Run once on mount; query params are read inside initializeWorkspace.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleNewChat = useCallback(async () => {
    setSwitchingThread(true);
    try {
      await startThread();
    } finally {
      setSwitchingThread(false);
    }
  }, [startThread]);

  const handleDeleteThread = useCallback(
    async (threadId: string) => {
      setError(null);

      try {
        await chatApi.deleteThread(threadId);
        const remaining = sortThreadsByUpdatedAt(
          threads.filter((item) => item.thread_id !== threadId),
        );
        setThreads(remaining);

        if (thread?.thread_id !== threadId) {
          return;
        }

        if (remaining.length > 0) {
          await selectThread(remaining[0].thread_id);
          return;
        }

        setSwitchingThread(true);
        try {
          await startThread();
        } finally {
          setSwitchingThread(false);
        }
      } catch (err) {
        setError((err as Error).message);
      }
    },
    [thread?.thread_id, threads, selectThread, startThread],
  );

  const handleSend = useCallback(
    async (text: string) => {
      if (!thread) return;

      const optimisticUserMessage: ChatMessage = {
        message_id: `temp-user-${Date.now()}`,
        thread_id: thread.thread_id,
        role: "user",
        content: text,
        metadata: {},
        created_at: new Date().toISOString(),
      };

      const streamingAssistantId = `temp-assistant-${Date.now()}`;
      const streamingAssistantMessage: ChatMessage = {
        message_id: streamingAssistantId,
        thread_id: thread.thread_id,
        role: "assistant",
        content: "",
        metadata: {},
        created_at: new Date().toISOString(),
      };

      setMessages((current) => [
        ...current,
        optimisticUserMessage,
        streamingAssistantMessage,
      ]);
      setStreamingMessageId(streamingAssistantId);
      setLoading(true);
      setError(null);
      setStreamErrorText(null);
      setRetryText(text);

      try {
        for await (const event of chatApi.sendMessageStream(
          thread.thread_id,
          text,
        )) {
          if (event.type === "chunk") {
            setMessages((current) =>
              current.map((message) =>
                message.message_id === streamingAssistantId
                  ? { ...message, content: message.content + event.text }
                  : message,
              ),
            );
          } else if (event.type === "meta") {
            const moduleLaunch = event.module_launch;

            if (shouldOpenPanel(moduleLaunch)) {
              openPanel(
                moduleLaunch!.module_type,
                moduleLaunchPanelState(moduleLaunch!),
                undefined,
                thread.thread_id,
              );
            }

            setMessages((current) =>
              current.map((message) =>
                message.message_id === streamingAssistantId
                  ? {
                      ...message,
                      metadata: {
                        suggestions: event.suggestions ?? [],
                        ...(moduleLaunch ? { module_launch: moduleLaunch } : {}),
                      },
                    }
                  : message,
              ),
            );

            const refreshed = await refreshThreads();
            const activeThread = refreshed.find(
              (item) => item.thread_id === thread.thread_id,
            );
            if (activeThread) {
              setThread(activeThread);
            } else if (event.title) {
              setThread((current) =>
                current
                  ? { ...current, title: event.title, updated_at: new Date().toISOString() }
                  : current,
              );
            }
          }
        }
      } catch (err) {
        setMessages((current) =>
          current.filter((message) => message.message_id !== streamingAssistantId),
        );
        setStreamErrorText((err as Error).message);
      } finally {
        setStreamingMessageId(null);
        setLoading(false);
      }
    },
    [thread, openPanel, refreshThreads],
  );

  const handleRetry = useCallback(() => {
    if (!retryText) return;
    setStreamErrorText(null);
    void handleSend(retryText);
  }, [retryText, handleSend]);

  const handleIntakeSubmit = useCallback(
    async (payload: IntakeSubmitPayload, messageId: string) => {
      if (!thread) return;

      setSubmittedIntakeMessageIds((current) => new Set(current).add(messageId));

      openPanel(
        payload.module_type,
        buildIntakePanelState(payload),
        payload,
        thread.thread_id,
      );

      const summary = formatIntakeSubmitMessage(payload);
      await handleSend(summary);
    },
    [thread, handleSend, openPanel],
  );

  useEffect(() => {
    if (!pendingMessage || !thread || initializing) {
      return;
    }

    const text = pendingMessage;
    setPendingMessage(null);
    void handleSend(text);
  }, [pendingMessage, thread, initializing, handleSend]);

  const chatDisabled = loading || switchingThread;

  return (
    <div className="space-y-8">
      <section>
        <Badge variant="secondary">Platform chat</Badge>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
          Carbon footprint assistant
        </h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Ask questions, explore your product data, and get guidance from the
          platform agent.
        </p>
      </section>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex overflow-hidden rounded-xl border bg-card shadow-xs">
        <ThreadList
          threads={threads}
          activeThreadId={thread?.thread_id ?? null}
          onSelect={(threadId) => void selectThread(threadId)}
          onNewChat={() => void handleNewChat()}
          onDelete={(threadId) => void handleDeleteThread(threadId)}
        />

        <Card className="min-w-0 flex-1 rounded-none border-0 shadow-none">
          <CardHeader className="border-b bg-card">
            <CardTitle>Chat</CardTitle>
            <CardDescription>
              {initializing
                ? "Starting a new conversation..."
                : thread?.title ?? "New conversation"}
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {initializing ? (
              <div className="flex min-h-[460px] items-center justify-center bg-secondary/40 p-6">
                <p className="text-sm text-muted-foreground">
                  Preparing your chat thread...
                </p>
              </div>
            ) : !thread ? (
              <div className="flex min-h-[460px] flex-col items-center justify-center gap-4 bg-secondary/40 p-6 text-center">
                <p className="max-w-md text-sm text-muted-foreground">
                  Could not start a chat thread. Check that the backend is
                  running and your environment variables are set, then try
                  again.
                </p>
                <Button onClick={() => void initializeWorkspace()} type="button">
                  Retry
                </Button>
              </div>
            ) : switchingThread ? (
              <div className="flex min-h-[460px] items-center justify-center bg-secondary/40 p-6">
                <p className="text-sm text-muted-foreground">
                  Loading conversation...
                </p>
              </div>
            ) : (
              <SplitLayout
                chat={
                  <>
                    <ChatThread
                      messages={messages}
                      loading={loading}
                      streamingMessageId={streamingMessageId}
                      errorText={streamErrorText}
                      submittedIntakeMessageIds={submittedIntakeMessageIds}
                      onSuggestionSelect={handleSend}
                      onIntakeSubmit={handleIntakeSubmit}
                      onRetry={handleRetry}
                    />
                    <ChatInput onSend={handleSend} disabled={chatDisabled} />
                  </>
                }
                panel={<PanelContainer />}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function ChatPageFallback() {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <p className="text-sm text-muted-foreground">Loading chat...</p>
    </div>
  );
}

export default function ChatPage() {
  return (
    <PanelProvider>
      <Suspense fallback={<ChatPageFallback />}>
        <ChatWorkspace />
      </Suspense>
    </PanelProvider>
  );
}
