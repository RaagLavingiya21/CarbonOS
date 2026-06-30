"use client";

import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ChatThread } from "@/lib/chat-api";
import { cn, formatRelativeTime } from "@/lib/utils";

interface ThreadListItemProps {
  thread: ChatThread;
  active: boolean;
  onSelect: (threadId: string) => void;
  onDelete: (threadId: string) => void;
}

export function ThreadListItem({
  thread,
  active,
  onSelect,
  onDelete,
}: ThreadListItemProps) {
  const title = thread.title ?? "New conversation";

  return (
    <div
      className={cn(
        "group flex items-center gap-1 rounded-md px-2 py-2 transition-colors hover:bg-secondary/80",
        active && "bg-secondary",
      )}
    >
      <button
        type="button"
        onClick={() => onSelect(thread.thread_id)}
        className="min-w-0 flex-1 text-left"
      >
        <p className="truncate text-sm font-medium">{title}</p>
        <p className="truncate text-xs text-muted-foreground">
          {formatRelativeTime(thread.updated_at)}
        </p>
      </button>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
        aria-label={`Delete ${title}`}
        onClick={(event) => {
          event.stopPropagation();
          onDelete(thread.thread_id);
        }}
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
