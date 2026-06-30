"use client";

import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { IntakeFormMessage } from "@/components/chat/forms/IntakeFormMessage";
import { SuggestionChips } from "@/components/chat/SuggestionChips";
import { Button } from "@/components/ui/button";
import type {
  ChatRole,
  IntakeForm,
  IntakeSubmitPayload,
  ModuleLaunch,
} from "@/lib/chat-api";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: ChatRole;
  content: string;
  suggestions?: string[];
  moduleLaunch?: ModuleLaunch | null;
  intakeFormSubmitted?: boolean;
  onSuggestionSelect?: (suggestion: string) => void;
  onIntakeSubmit?: (payload: IntakeSubmitPayload) => void;
  suggestionsDisabled?: boolean;
  streaming?: boolean;
  variant?: "default" | "error";
  onRetry?: () => void;
}

function getIntakeForm(moduleLaunch?: ModuleLaunch | null): IntakeForm | null {
  if (
    moduleLaunch?.step === "intake" &&
    moduleLaunch.intake_form &&
    typeof moduleLaunch.intake_form === "object"
  ) {
    return moduleLaunch.intake_form;
  }
  return null;
}

function StreamingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
    </span>
  );
}

export function ChatMessage({
  role,
  content,
  suggestions = [],
  moduleLaunch,
  intakeFormSubmitted = false,
  onSuggestionSelect,
  onIntakeSubmit,
  suggestionsDisabled = false,
  streaming = false,
  variant = "default",
  onRetry,
}: ChatMessageProps) {
  const isUser = role === "user";
  const isError = variant === "error";
  const intakeForm = getIntakeForm(moduleLaunch);
  const showIntakeForm =
    !isUser && intakeForm && onIntakeSubmit && !intakeFormSubmitted && !isError;

  return (
    <div
      className={cn(
        "flex gap-3",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      {!isUser ? (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <Bot className="h-4 w-4" />
        </div>
      ) : null}
      <div className={cn("max-w-[82%]", isUser ? "" : "flex flex-col")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-sm shadow-xs",
            isUser
              ? "bg-primary text-primary-foreground"
              : isError
                ? "border border-destructive/40 bg-destructive/10 text-destructive"
                : "bg-card prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-headings:my-2",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : isError ? (
            <div className="space-y-3">
              <p className="whitespace-pre-wrap">{content}</p>
              {onRetry ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="border-destructive/40 text-destructive hover:bg-destructive/10"
                  onClick={onRetry}
                >
                  Retry
                </Button>
              ) : null}
            </div>
          ) : (
            <>
              {content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content}
                </ReactMarkdown>
              ) : null}
              {streaming ? <StreamingDots /> : null}
              {showIntakeForm ? (
                <IntakeFormMessage
                  intakeForm={intakeForm}
                  disabled={suggestionsDisabled}
                  onSubmit={onIntakeSubmit}
                />
              ) : null}
            </>
          )}
        </div>
        {!isUser && onSuggestionSelect && !isError ? (
          <SuggestionChips
            suggestions={suggestions}
            onSelect={onSuggestionSelect}
            disabled={suggestionsDisabled}
          />
        ) : null}
      </div>
      {isUser ? (
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white">
          <User className="h-4 w-4" />
        </div>
      ) : null}
    </div>
  );
}
