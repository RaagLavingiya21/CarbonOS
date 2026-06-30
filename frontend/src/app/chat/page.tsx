"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatThread } from "@/components/chat/ChatThread";
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

function ChatWorkspace() {
  const { openPanel } = usePanels();
  const [thread, setThread] = useState<ChatThreadType | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submittedIntakeMessageIds, setSubmittedIntakeMessageIds] = useState<
    Set<string>
  >(() => new Set());
  const pendingIntakePayloadsRef = useRef<Map<string, IntakeSubmitPayload>>(
    new Map(),
  );

  const startThread = useCallback(async () => {
    setInitializing(true);
    setError(null);
    try {
      const created = await chatApi.createThread();
      setThread(created);
      setMessages([]);
      setSubmittedIntakeMessageIds(new Set());
      pendingIntakePayloadsRef.current.clear();
    } catch (err) {
      setThread(null);
      setError((err as Error).message);
    } finally {
      setInitializing(false);
    }
  }, []);

  useEffect(() => {
    void startThread();
  }, [startThread]);

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

      setMessages((current) => [...current, optimisticUserMessage]);
      setLoading(true);
      setError(null);

      try {
        const response = await chatApi.sendMessage(thread.thread_id, text);
        const moduleLaunch = response.module_launch;

        if (shouldOpenPanel(moduleLaunch)) {
          openPanel(
            moduleLaunch!.module_type,
            moduleLaunchPanelState(moduleLaunch!),
          );
        }

        const assistantMessage: ChatMessage = {
          message_id: `temp-assistant-${Date.now()}`,
          thread_id: thread.thread_id,
          role: "assistant",
          content: response.content,
          metadata: {
            suggestions: response.suggestions ?? [],
            ...(moduleLaunch ? { module_launch: moduleLaunch } : {}),
          },
          created_at: new Date().toISOString(),
        };
        setMessages((current) => [...current, assistantMessage]);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [thread, openPanel],
  );

  const handleIntakeSubmit = useCallback(
    async (payload: IntakeSubmitPayload, messageId: string) => {
      if (!thread) return;

      pendingIntakePayloadsRef.current.set(messageId, payload);
      setSubmittedIntakeMessageIds((current) => new Set(current).add(messageId));

      const summary = formatIntakeSubmitMessage(payload);
      await handleSend(summary);
    },
    [thread, handleSend],
  );

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

      <Card className="overflow-hidden">
        <CardHeader className="border-b bg-white">
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
                Could not start a chat thread. Check that the backend is running
                and your environment variables are set, then try again.
              </p>
              <Button onClick={() => void startThread()} type="button">
                Retry
              </Button>
            </div>
          ) : (
            <SplitLayout
              chat={
                <>
                  <ChatThread
                    messages={messages}
                    loading={loading}
                    submittedIntakeMessageIds={submittedIntakeMessageIds}
                    onSuggestionSelect={handleSend}
                    onIntakeSubmit={handleIntakeSubmit}
                  />
                  <ChatInput onSend={handleSend} disabled={loading} />
                </>
              }
              panel={<PanelContainer />}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function ChatPage() {
  return (
    <PanelProvider>
      <ChatWorkspace />
    </PanelProvider>
  );
}
