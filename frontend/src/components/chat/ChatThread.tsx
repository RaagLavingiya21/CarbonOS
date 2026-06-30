"use client";

import { useEffect, useRef } from "react";
import { Bot } from "lucide-react";

import { ChatMessage } from "@/components/chat/ChatMessage";
import type {
  ChatMessage as ChatMessageType,
  IntakeSubmitPayload,
  ModuleLaunch,
} from "@/lib/chat-api";

interface ChatThreadProps {
  messages: ChatMessageType[];
  loading: boolean;
  streamingMessageId?: string | null;
  errorText?: string | null;
  submittedIntakeMessageIds?: Set<string>;
  onSuggestionSelect?: (suggestion: string) => void;
  onIntakeSubmit?: (payload: IntakeSubmitPayload, messageId: string) => void;
  onRetry?: () => void;
}

function getModuleLaunch(message: ChatMessageType): ModuleLaunch | null {
  const moduleLaunch = message.metadata?.module_launch;
  if (moduleLaunch && typeof moduleLaunch === "object") {
    return moduleLaunch as ModuleLaunch;
  }
  return null;
}

function TypingIndicator() {
  return (
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
  );
}

export function ChatThread({
  messages,
  loading,
  streamingMessageId,
  errorText,
  submittedIntakeMessageIds,
  onSuggestionSelect,
  onIntakeSubmit,
  onRetry,
}: ChatThreadProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, errorText, streamingMessageId]);

  const visibleMessages = messages.filter(
    (message) => message.role === "user" || message.role === "assistant",
  );

  const showStandaloneTyping =
    loading && !streamingMessageId && !errorText;

  return (
    <div className="max-h-[58vh] min-h-[460px] space-y-5 overflow-y-auto bg-secondary/40 p-4 md:p-6">
      {visibleMessages.map((message) => (
        <ChatMessage
          key={message.message_id}
          role={message.role}
          content={message.content}
          suggestions={
            Array.isArray(message.metadata?.suggestions)
              ? message.metadata.suggestions
              : []
          }
          moduleLaunch={getModuleLaunch(message)}
          intakeFormSubmitted={submittedIntakeMessageIds?.has(message.message_id)}
          onSuggestionSelect={onSuggestionSelect}
          onIntakeSubmit={
            onIntakeSubmit
              ? (payload) => onIntakeSubmit(payload, message.message_id)
              : undefined
          }
          suggestionsDisabled={loading}
          streaming={
            message.message_id === streamingMessageId && message.role === "assistant"
          }
        />
      ))}
      {showStandaloneTyping ? <TypingIndicator /> : null}
      {errorText ? (
        <ChatMessage
          role="assistant"
          content={errorText}
          variant="error"
          onRetry={onRetry}
        />
      ) : null}
      <div ref={messagesEndRef} />
    </div>
  );
}
