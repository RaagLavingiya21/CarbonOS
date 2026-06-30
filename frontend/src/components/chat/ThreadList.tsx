"use client";

import { useEffect, useMemo, useState } from "react";
import { PanelLeft, PanelLeftClose, Plus } from "lucide-react";

import { ThreadListItem } from "@/components/chat/ThreadListItem";
import { Button } from "@/components/ui/button";
import type { ChatThread } from "@/lib/chat-api";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "chat-thread-sidebar-collapsed";

interface ThreadListProps {
  threads: ChatThread[];
  activeThreadId: string | null;
  onSelect: (threadId: string) => void;
  onNewChat: () => void;
  onDelete: (threadId: string) => void;
}

function readCollapsedState(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return localStorage.getItem(STORAGE_KEY) === "true";
}

export function ThreadList({
  threads,
  activeThreadId,
  onSelect,
  onNewChat,
  onDelete,
}: ThreadListProps) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    setCollapsed(readCollapsedState());
  }, []);

  const sortedThreads = useMemo(
    () =>
      [...threads].sort(
        (left, right) =>
          new Date(right.updated_at).getTime() -
          new Date(left.updated_at).getTime(),
      ),
    [threads],
  );

  const toggleCollapsed = () => {
    setCollapsed((current) => {
      const next = !current;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  };

  if (collapsed) {
    return (
      <aside className="flex w-12 shrink-0 flex-col items-center border-r bg-card py-3">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Expand chat history"
          onClick={toggleCollapsed}
        >
          <PanelLeft className="h-4 w-4" />
        </Button>
      </aside>
    );
  }

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r bg-card">
      <div className="flex items-center gap-2 border-b px-3 py-3">
        <Button
          type="button"
          className="flex-1 justify-start gap-2"
          onClick={onNewChat}
        >
          <Plus className="h-4 w-4" />
          New chat
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="Collapse chat history"
          onClick={toggleCollapsed}
        >
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-2">
        {sortedThreads.length === 0 ? (
          <p className="px-2 py-4 text-sm text-muted-foreground">
            No conversations yet.
          </p>
        ) : (
          <div className={cn("space-y-1")}>
            {sortedThreads.map((thread) => (
              <ThreadListItem
                key={thread.thread_id}
                thread={thread}
                active={thread.thread_id === activeThreadId}
                onSelect={onSelect}
                onDelete={onDelete}
              />
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
