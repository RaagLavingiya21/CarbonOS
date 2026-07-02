"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  FileSearch,
  Factory,
  MessageSquare,
  UploadCloud,
} from "lucide-react";

import { ChatInput } from "@/components/chat/ChatInput";
import {
  ModuleShowcaseCard,
  type ModuleShowcaseData,
} from "@/components/dashboard/ModuleShowcaseCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { chatApi, type ChatThread } from "@/lib/chat-api";
import { cn, formatRelativeTime } from "@/lib/utils";

const MODULES: ModuleShowcaseData[] = [
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
  const [recentThreads, setRecentThreads] = useState<ChatThread[]>([]);
  const [loadingThreads, setLoadingThreads] = useState(true);

  useEffect(() => {
    chatApi
      .listThreads()
      .then((threads) => setRecentThreads(sortThreadsByUpdatedAt(threads).slice(0, 5)))
      .catch(() => setRecentThreads([]))
      .finally(() => setLoadingThreads(false));
  }, []);

  const router = useRouter();

  const handleSend = useCallback(
    (message: string) => {
      router.push(`/chat?message=${encodeURIComponent(message)}`);
    },
    [router],
  );

  return (
    <div className="mx-auto flex max-w-4xl flex-col items-center gap-12 py-4 md:py-10">
      <section className="w-full space-y-4 text-center">
        <h1 className="text-h1 font-medium text-balance md:text-display">
          Carbon footprint assistant
        </h1>
        <p className="mx-auto max-w-xl text-body-lg text-muted-foreground text-pretty">
          Analyze bills of materials, close Scope 3 data gaps, and engage
          suppliers — all from one conversation with your platform agent.
        </p>
        <div className="mx-auto w-full max-w-2xl text-left">
          <ChatInput variant="hero" onSend={handleSend} showModuleButtons={false} />
        </div>
      </section>

      <section className="w-full">
        <h2 className="mb-4 text-center text-sm font-medium text-muted-foreground">
          Explore the modules
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {MODULES.map((module) => (
            <ModuleShowcaseCard key={module.name} {...module} />
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
