"use client";

import { useCallback, useEffect, useState } from "react";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatThread } from "@/components/chat/ChatThread";
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
  type ChatMessage,
  type ChatThread as ChatThreadType,
} from "@/lib/chat-api";

export default function ChatPage() {
  const [thread, setThread] = useState<ChatThreadType | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startThread = useCallback(async () => {
    setInitializing(true);
    setError(null);
    try {
      const created = await chatApi.createThread();
      setThread(created);
      setMessages([]);
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
        const assistantMessage: ChatMessage = {
          message_id: `temp-assistant-${Date.now()}`,
          thread_id: thread.thread_id,
          role: "assistant",
          content: response.content,
          metadata: { suggestions: response.suggestions ?? [] },
          created_at: new Date().toISOString(),
        };
        setMessages((current) => [...current, assistantMessage]);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [thread],
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
            <>
              <ChatThread
                messages={messages}
                loading={loading}
                onSuggestionSelect={handleSend}
              />
              <ChatInput onSend={handleSend} disabled={loading} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
