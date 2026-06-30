"use client";

import { useEffect, useRef } from "react";
import { Bot } from "lucide-react";

import { ChatMessage } from "@/components/chat/ChatMessage";
import type { ChatMessage as ChatMessageType } from "@/lib/chat-api";

interface ChatThreadProps {
  messages: ChatMessageType[];
  loading: boolean;
  onSuggestionSelect?: (suggestion: string) => void;
}

export function ChatThread({
  messages,
  loading,
  onSuggestionSelect,
}: ChatThreadProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const visibleMessages = messages.filter(
    (message) => message.role === "user" || message.role === "assistant",
  );

  return (
    <div className="max-h-[58vh] min-h-[460px] space-y-5 overflow-y-auto bg-secondary/40 p-4 md:p-6">
      {visibleMessages.map((message) => (
        <ChatMessage
          key={message.message_id}
          role={message.role}
          content={message.content}
          suggestions={
            Array.isArray(message.metadata?.suggestions)
              ? (message.metadata.suggestions as string[])
              : []
          }
          onSuggestionSelect={onSuggestionSelect}
          suggestionsDisabled={loading}
        />
      ))}
      {loading ? (
        <div className="flex gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-primary-foreground">
            <Bot className="h-4 w-4" />
          </div>
          <div className="rounded-2xl bg-white px-4 py-3 text-sm shadow-sm">
            <span className="inline-flex items-center gap-1">
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
            </span>
          </div>
        </div>
      ) : null}
      <div ref={messagesEndRef} />
    </div>
  );
}
