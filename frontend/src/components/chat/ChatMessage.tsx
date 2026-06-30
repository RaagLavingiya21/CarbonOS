"use client";

import { Bot, User } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { IntakeFormMessage } from "@/components/chat/forms/IntakeFormMessage";
import { SuggestionChips } from "@/components/chat/SuggestionChips";
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

export function ChatMessage({
  role,
  content,
  suggestions = [],
  moduleLaunch,
  intakeFormSubmitted = false,
  onSuggestionSelect,
  onIntakeSubmit,
  suggestionsDisabled = false,
}: ChatMessageProps) {
  const isUser = role === "user";
  const intakeForm = getIntakeForm(moduleLaunch);
  const showIntakeForm =
    !isUser && intakeForm && onIntakeSubmit && !intakeFormSubmitted;

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
            "rounded-2xl px-4 py-3 text-sm shadow-sm",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-white prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-headings:my-2",
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <>
              {content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {content}
                </ReactMarkdown>
              ) : null}
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
        {!isUser && onSuggestionSelect ? (
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
