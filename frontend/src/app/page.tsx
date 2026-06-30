"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  FileSearch,
  FileUp,
  Factory,
  Flame,
  GitCompare,
  HelpCircle,
  Mail,
  MessageSquare,
  Search,
  Send,
  UploadCloud,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import {
  ModuleFlipCard,
  type ModuleFlipCardData,
} from "@/components/dashboard/ModuleFlipCard";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { chatApi, type ChatThread } from "@/lib/chat-api";
import { cn, formatRelativeTime } from "@/lib/utils";

interface PromptSuggestion {
  title: string;
  subtitle: string;
  icon: LucideIcon;
  message: string;
}

const PROMPT_SUGGESTIONS: PromptSuggestion[] = [
  {
    title: "Analyze a bill of materials",
    subtitle: "Upload a BOM and estimate product emissions",
    icon: FileUp,
    message: "Analyze a bill of materials",
  },
  {
    title: "Check my Scope 3 gaps",
    subtitle: "Find missing data and coverage gaps",
    icon: Search,
    message: "Check my Scope 3 gaps",
  },
  {
    title: "Draft a supplier email",
    subtitle: "Start supplier engagement outreach",
    icon: Mail,
    message: "Draft a supplier email",
  },
  {
    title: "What is Scope 3?",
    subtitle: "Learn GHG Protocol fundamentals",
    icon: HelpCircle,
    message: "What is Scope 3?",
  },
  {
    title: "Compare my product footprints",
    subtitle: "See emissions across saved analyses",
    icon: GitCompare,
    message: "Compare my product footprints",
  },
  {
    title: "Show my highest hotspots",
    subtitle: "Identify the most emitting materials",
    icon: Flame,
    message: "Show my highest hotspots",
  },
];

const MODULE_FLIP_CARDS: ModuleFlipCardData[] = [
  {
    name: "Analyzer",
    icon: UploadCloud,
    job: "Estimate a product's footprint from its BOM.",
    problem:
      "Bills of materials are messy, and there's no easy way to get a Scope 3 number out of them.",
    steps: [
      "Parse & clean the uploaded BOM",
      "Match each line to an emission factor",
      "Calculate the footprint & rank hotspots",
    ],
    ctaLabel: "Analyze a BOM",
    message: "I want to analyze a bill of materials",
  },
  {
    name: "Gap Analyzer",
    icon: FileSearch,
    job: "Find what's missing in your Scope 3 data.",
    problem:
      "You can't improve what you can't measure — and data gaps hide your biggest risks.",
    steps: [
      "Assess your reporting requirements",
      "Score what's material",
      "Surface data gaps & next steps",
    ],
    ctaLabel: "Check my gaps",
    message: "Check my Scope 3 gaps",
  },
  {
    name: "Supplier Copilot",
    icon: Factory,
    job: "Engage the right suppliers first.",
    problem:
      "Supplier outreach is slow and unfocused; you need to start with the highest-impact ones.",
    steps: [
      "Rank suppliers by emission impact",
      "Draft a GHG-grounded data request",
      "Track responses",
    ],
    ctaLabel: "Start engagement",
    message: "Draft a supplier email",
  },
  {
    name: "Advisor",
    icon: MessageSquare,
    job: "Ask anything about your footprints & the GHG Protocol.",
    problem:
      "Methodology questions and your own data live in different places.",
    steps: [
      "Ask in plain language",
      "Grounded in your data + GHG Protocol",
      "Answers cite their sources",
    ],
    ctaLabel: "Open chat",
    message: "What can you help me with?",
  },
];

function sortThreadsByUpdatedAt(threads: ChatThread[]): ChatThread[] {
  return [...threads].sort(
    (left, right) =>
      new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
  );
}

export default function Home() {
  const router = useRouter();
  const [input, setInput] = useState("");
  const [recentThreads, setRecentThreads] = useState<ChatThread[]>([]);
  const [loadingThreads, setLoadingThreads] = useState(true);

  useEffect(() => {
    chatApi
      .listThreads()
      .then((threads) => setRecentThreads(sortThreadsByUpdatedAt(threads).slice(0, 5)))
      .catch(() => setRecentThreads([]))
      .finally(() => setLoadingThreads(false));
  }, []);

  const navigateToChat = useCallback(
    (message: string) => {
      router.push(`/chat?message=${encodeURIComponent(message)}`);
    },
    [router],
  );

  const handleSubmit = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed) return;
    navigateToChat(trimmed);
  }, [input, navigateToChat]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  return (
    <div className="mx-auto flex max-w-4xl flex-col items-center gap-12 py-4 md:py-10">
      <section className="space-y-3 text-center">
        <h1 className="text-h1 font-medium text-balance md:text-display">
          Carbon footprint assistant
        </h1>
        <p className="mx-auto max-w-xl text-body-lg text-muted-foreground text-pretty">
          Ask questions, analyze bills of materials, and explore Scope 3 hotspots
          — all from one conversation.
        </p>
      </section>

      <section className="w-full max-w-2xl">
        <div className="flex items-center gap-2 rounded-lg border bg-card px-4 py-2 shadow-xs transition-shadow duration-micro focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background">
          <Input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about your product footprints…"
            className="border-0 bg-transparent text-body shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
          />
          <Button
            type="button"
            size="icon"
            className="shrink-0 rounded-xl"
            disabled={!input.trim()}
            onClick={handleSubmit}
            aria-label="Send message"
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </section>

      <section className="w-full">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {PROMPT_SUGGESTIONS.map(({ title, subtitle, icon: Icon, message }) => (
            <button
              key={title}
              type="button"
              onClick={() => navigateToChat(message)}
              className="group text-left"
            >
              <Card className="h-full transition-[border-color,box-shadow,transform] duration-micro ease-out hover:-translate-y-0.5 hover:border-border hover:shadow-xs">
                <CardHeader className="pb-2">
                  <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <CardTitle className="text-sm font-medium leading-snug">
                    {title}
                  </CardTitle>
                  <CardDescription className="text-xs">{subtitle}</CardDescription>
                </CardHeader>
              </Card>
            </button>
          ))}
        </div>
      </section>

      <section className="w-full">
        <h2 className="mb-4 text-center text-sm font-medium text-muted-foreground">
          Or start with a module
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {MODULE_FLIP_CARDS.map((module) => (
            <ModuleFlipCard key={module.name} {...module} />
          ))}
        </div>
      </section>

      {!loadingThreads && recentThreads.length > 0 ? (
        <section className="w-full">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-medium">Recent conversations</h2>
            <Button asChild variant="ghost" size="sm" className="text-muted-foreground">
              <Link href="/chat">
                View all
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          </div>
          <Card>
            <CardContent className="divide-y p-0">
              {recentThreads.map((thread) => (
                <Link
                  key={thread.thread_id}
                  href={`/chat?thread=${thread.thread_id}`}
                  className={cn(
                    "flex items-center justify-between gap-4 px-4 py-3 transition hover:bg-accent/50",
                  )}
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {thread.title ?? "New conversation"}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatRelativeTime(thread.updated_at)}
                    </p>
                  </div>
                  <BarChart3 className="h-4 w-4 shrink-0 text-muted-foreground" />
                </Link>
              ))}
            </CardContent>
          </Card>
        </section>
      ) : null}
    </div>
  );
}
