"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Plus } from "lucide-react";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatThread } from "@/components/chat/ChatThread";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  chatApi,
  type ChatMessage,
  type ChatThread as ChatThreadType,
  type ModuleLaunch,
} from "@/lib/chat-api";

interface ChatDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function sortThreadsByUpdatedAt(threads: ChatThreadType[]): ChatThreadType[] {
  return [...threads].sort(
    (left, right) =>
      new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  );
}

export function ChatDrawer({ open, onOpenChange }: ChatDrawerProps) {
  const [thread, setThread] = useState<ChatThreadType | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [initializing, setInitializing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [moduleLaunchNotice, setModuleLaunchNotice] = useState<ModuleLaunch | null>(
    null,
  );

  const loadWorkspace = useCallback(async () => {
    setInitializing(true);
    setError(null);
    setModuleLaunchNotice(null);

    try {
      const listed = sortThreadsByUpdatedAt(await chatApi.listThreads());

      if (listed.length > 0) {
        const detail = await chatApi.getThread(listed[0].thread_id);
        setThread(detail.thread);
        setMessages(detail.messages);
      } else {
        const created = await chatApi.createThread();
        setThread(created);
        setMessages([]);
      }
    } catch (err) {
      setThread(null);
      setMessages([]);
      setError((err as Error).message);
    } finally {
      setInitializing(false);
    }
  }, []);

  useEffect(() => {
    if (!open) {
      return;
    }

    void loadWorkspace();
  }, [open, loadWorkspace]);

  const handleNewChat = useCallback(async () => {
    setError(null);
    setModuleLaunchNotice(null);

    try {
      const created = await chatApi.createThread();
      setThread(created);
      setMessages([]);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

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
      setModuleLaunchNotice(null);

      try {
        const response = await chatApi.sendMessage(thread.thread_id, text);
        const moduleLaunch = response.module_launch;

        if (moduleLaunch) {
          setModuleLaunchNotice(moduleLaunch);
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

        const listed = sortThreadsByUpdatedAt(await chatApi.listThreads());
        const activeThread = listed.find(
          (item) => item.thread_id === thread.thread_id,
        );
        if (activeThread) {
          setThread(activeThread);
        }
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [thread],
  );

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 p-0 sm:max-w-[420px]"
      >
        <SheetHeader className="space-y-3 border-b px-4 py-4 pr-12 text-left">
          <div className="flex items-start justify-between gap-3">
            <div>
              <SheetTitle>AI Assistant</SheetTitle>
              <SheetDescription>
                {initializing
                  ? "Loading conversation..."
                  : thread?.title ?? "New conversation"}
              </SheetDescription>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => void handleNewChat()}
                disabled={initializing || loading}
              >
                <Plus className="h-4 w-4" />
                New
              </Button>
              <Button type="button" variant="ghost" size="sm" asChild>
                <Link href="/chat">
                  <ExternalLink className="h-4 w-4" />
                  Full chat
                </Link>
              </Button>
            </div>
          </div>
        </SheetHeader>

        {error ? (
          <Alert variant="destructive" className="mx-4 mt-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        {moduleLaunchNotice ? (
          <Alert className="mx-4 mt-4">
            <AlertDescription>
              This action needs the full chat workspace.{" "}
              <Link href="/chat" className="font-medium text-primary underline">
                Open full chat to continue
              </Link>
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {initializing ? (
            <div className="flex flex-1 items-center justify-center p-6">
              <p className="text-sm text-muted-foreground">
                Preparing your chat thread...
              </p>
            </div>
          ) : !thread ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center">
              <p className="text-sm text-muted-foreground">
                Could not start a chat thread. Check that the backend is running,
                then try again.
              </p>
              <Button type="button" onClick={() => void loadWorkspace()}>
                Retry
              </Button>
            </div>
          ) : (
            <>
              <div className="min-h-0 flex-1 [&>div]:h-full [&>div]:max-h-none [&>div]:min-h-0">
                <ChatThread
                  messages={messages}
                  loading={loading}
                  onSuggestionSelect={handleSend}
                />
              </div>
              <ChatInput
                onSend={handleSend}
                disabled={loading}
                showModuleButtons={false}
              />
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
