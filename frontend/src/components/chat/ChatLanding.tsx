"use client";

import { useState } from "react";
import {
  BookOpen,
  ChevronRight,
  Factory,
  FileSearch,
  Flame,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";

import { ChatInput } from "@/components/chat/ChatInput";
import type { ChatThread } from "@/lib/chat-api";
import { cn, formatRelativeTime } from "@/lib/utils";

type Workflow = { icon: LucideIcon; label: string; hint: string; accent: string; prompt: string };

const WORKFLOWS: Workflow[] = [
  {
    icon: UploadCloud,
    label: "Analyze a BOM",
    hint: "Upload a bill of materials → hotspot report",
    accent: "text-primary",
    prompt: "I want to analyze a bill of materials",
  },
  {
    icon: FileSearch,
    label: "Run gap analysis",
    hint: "Find where supplier data can replace estimates",
    accent: "text-data-info",
    prompt: "Run a gap analysis on my portfolio's primary data coverage",
  },
  {
    icon: Factory,
    label: "Engage suppliers",
    hint: "Draft & send data requests to your vendors",
    accent: "text-data-medium",
    prompt: "Help me draft supplier engagement requests for missing emission data",
  },
  {
    icon: Sparkles,
    label: "Ask the advisor",
    hint: "Methodology, disclosures, reduction targets",
    accent: "text-data-low",
    prompt: "Ask the carbon advisor about methodology and reporting",
  },
];

type Topic = { icon: LucideIcon; label: string; accent: string; questions: string[] };

const TOPICS: Topic[] = [
  {
    icon: Flame,
    label: "Hotspots & impact",
    accent: "text-primary",
    questions: [
      "Show my highest emission hotspots across the portfolio",
      "Which products drive most of my Scope 3 footprint?",
      "Compare this quarter's hotspots to last quarter",
    ],
  },
  {
    icon: ShieldCheck,
    label: "Data quality",
    accent: "text-data-medium",
    questions: [
      "Which products are missing primary supplier data?",
      "Flag BOM rows with low-confidence emission factors",
      "What's my portfolio-wide primary-data coverage?",
    ],
  },
  {
    icon: Factory,
    label: "Suppliers",
    accent: "text-data-info",
    questions: [
      "Draft a supplier request for packaging emissions",
      "Which suppliers haven't responded in 30 days?",
      "Rank suppliers by data completeness",
    ],
  },
  {
    icon: BookOpen,
    label: "Methodology",
    accent: "text-data-low",
    questions: [
      "How do I allocate Scope 3 Cat 1 for multi-material products?",
      "When should I use EEIO vs Ecoinvent factors?",
      "What GHG Protocol rule applies to co-products?",
    ],
  },
];

/**
 * Chat empty-state landing — workflow launchers, suggested topics, and recent
 * threads. Everything routes through the existing wired handlers (`onSend`,
 * `onSelectThread`); this component adds no new data flow.
 */
export function ChatLanding({
  onSend,
  disabled,
  threads,
  onSelectThread,
}: {
  onSend: (text: string) => void;
  disabled?: boolean;
  threads: ChatThread[];
  onSelectThread: (threadId: string) => void;
}) {
  const [activeTopic, setActiveTopic] = useState(TOPICS[0].label);
  const topic = TOPICS.find((t) => t.label === activeTopic) ?? TOPICS[0];
  const recent = threads.slice(0, 3);

  return (
    <div className="mx-auto w-full max-w-[720px] flex-1 overflow-y-auto px-6 pb-16">
      <div className="pt-12 pb-6">
        <div className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-2 py-0.5 text-caption font-medium text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-primary" />
          Scope 3 workspace
        </div>
        <h1 className="text-h1 font-semibold tracking-tight text-foreground">
          What are we measuring today?
        </h1>
        <p className="mt-1.5 text-body text-muted-foreground">
          Ask anything about your carbon data, or launch a workflow below. Complex workflows open a
          workspace beside this chat.
        </p>
      </div>

      <ChatInput variant="hero" onSend={onSend} disabled={disabled} showModuleButtons={false} />

      {/* Workflow launchers */}
      <div className="mt-6">
        <SectionLabel>Launch a workflow</SectionLabel>
        <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
          {WORKFLOWS.map((w) => {
            const Icon = w.icon;
            return (
              <button
                key={w.label}
                type="button"
                disabled={disabled}
                onClick={() => onSend(w.prompt)}
                className="group flex items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2.5 text-left transition-all hover:border-border-strong hover:shadow-xs disabled:opacity-50"
              >
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-muted">
                  <Icon className={cn("h-4 w-4", w.accent)} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-body font-medium text-foreground">{w.label}</span>
                  <span className="block truncate text-caption text-muted-foreground">{w.hint}</span>
                </span>
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </button>
            );
          })}
        </div>
      </div>

      {/* Try asking */}
      <div className="mt-6">
        <SectionLabel>Try asking</SectionLabel>
        <div className="rounded-lg border border-border bg-surface">
          <div className="flex items-center gap-0.5 overflow-x-auto border-b border-border px-1.5 py-1.5">
            {TOPICS.map((t) => {
              const Icon = t.icon;
              const active = t.label === activeTopic;
              return (
                <button
                  key={t.label}
                  type="button"
                  onClick={() => setActiveTopic(t.label)}
                  className={cn(
                    "flex items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-1 text-small font-medium transition-colors",
                    active
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                  )}
                >
                  <Icon className={cn("h-3.5 w-3.5", active && t.accent)} />
                  {t.label}
                </button>
              );
            })}
          </div>
          <div className="divide-y divide-border">
            {topic.questions.map((q) => (
              <button
                key={q}
                type="button"
                disabled={disabled}
                onClick={() => onSend(q)}
                className="group flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-muted/50 disabled:opacity-50"
              >
                <span className="text-muted-foreground/60 group-hover:text-primary">→</span>
                <span className="flex-1 text-body text-foreground">{q}</span>
                <span className="text-caption text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
                  Ask
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Recent */}
      {recent.length > 0 ? (
        <div className="mt-8">
          <SectionLabel>Recent</SectionLabel>
          <div className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface">
            {recent.map((r) => (
              <button
                key={r.thread_id}
                type="button"
                onClick={() => onSelectThread(r.thread_id)}
                className="group flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-muted/60"
              >
                <span className="min-w-0 flex-1 truncate text-body text-foreground">
                  {r.title ?? "New conversation"}
                </span>
                <span className="shrink-0 text-caption text-muted-foreground">
                  {formatRelativeTime(r.updated_at)}
                </span>
                <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-center gap-2 text-caption font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}
