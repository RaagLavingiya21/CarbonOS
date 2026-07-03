"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ChevronRight,
  Clock,
  Factory,
  FileSearch,
  Flag,
  MessageSquare,
  Sparkles,
  UploadCloud,
  type LucideIcon,
} from "lucide-react";

import { KpiStrip, type KpiTileData } from "@/components/portfolio/KpiStrip";
import { StatusChip } from "@/components/portfolio/StatusChip";
import { Placeholder } from "@/components/portfolio/Placeholder";
import { Skeleton } from "@/components/ui/skeleton";
import { chatApi, type ChatThread } from "@/lib/chat-api";
import { api, type AnalysisSummary, type PortfolioSummary } from "@/lib/api";
import { cn, formatRelativeTime } from "@/lib/utils";

type ModuleTileData = {
  name: string;
  icon: LucideIcon;
  desc: string;
  message: string;
  accent: string;
};

const MODULES: ModuleTileData[] = [
  {
    name: "Analyzer",
    icon: UploadCloud,
    desc: "Estimate a product's footprint from its BOM",
    message: "I want to analyze a bill of materials",
    accent: "text-primary",
  },
  {
    name: "Gap Analyzer",
    icon: FileSearch,
    desc: "Find what's missing in your Scope 3 data",
    message: "Check my Scope 3 gaps",
    accent: "text-data-info",
  },
  {
    name: "Supplier Copilot",
    icon: Factory,
    desc: "Engage the highest-impact suppliers first",
    message: "Draft a supplier email",
    accent: "text-data-medium",
  },
  {
    name: "Advisor",
    icon: MessageSquare,
    desc: "Ask anything about your data & the GHG Protocol",
    message: "What can you help me with?",
    accent: "text-data-low",
  },
];

function compactNumber(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "0";
  return new Intl.NumberFormat("en", {
    maximumFractionDigits: value >= 100 ? 0 : 1,
  }).format(value);
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

/* ---- Attention queue derivation (from real analyses) ---- */

type AttentionKind = "flag" | "review" | "stale" | "attention";

type AttentionItem = {
  productId: number;
  title: string;
  meta: string;
  status?: string | null;
  kind: AttentionKind;
  severity: number; // higher = more urgent
  updated?: string | null;
};

function toAttentionItem(a: AnalysisSummary): AttentionItem | null {
  const flagged = a.flagged_items ?? 0;
  const health = (a.health_status ?? "").toLowerCase();
  const status = (a.status ?? "").toLowerCase();
  const reason = a.health_reasons?.[0];

  if (flagged > 0) {
    return {
      productId: a.product_id,
      title: a.product_name,
      meta: reason ?? `${flagged} flagged line item${flagged === 1 ? "" : "s"}`,
      status: a.status,
      kind: "flag",
      severity: 3,
      updated: a.analysis_date,
    };
  }
  if (status === "under_review") {
    return {
      productId: a.product_id,
      title: a.product_name,
      meta: reason ?? "Awaiting review",
      status: a.status,
      kind: "review",
      severity: 2,
      updated: a.submitted_at ?? a.analysis_date,
    };
  }
  if (health === "stale") {
    return {
      productId: a.product_id,
      title: a.product_name,
      meta: reason ?? "Footprint is stale — consider recalculating",
      status: a.status,
      kind: "stale",
      severity: 2,
      updated: a.analysis_date,
    };
  }
  if (health === "attention") {
    return {
      productId: a.product_id,
      title: a.product_name,
      meta: reason ?? "Needs attention",
      status: a.status,
      kind: "attention",
      severity: 1,
      updated: a.analysis_date,
    };
  }
  return null;
}

const ATTENTION_META: Record<
  AttentionKind,
  { label: string; Icon: LucideIcon; className: string }
> = {
  flag: { label: "Flag", Icon: Flag, className: "bg-data-medium-bg text-data-medium" },
  review: { label: "Review", Icon: Clock, className: "bg-primary/10 text-primary" },
  stale: { label: "Stale", Icon: AlertTriangle, className: "bg-data-high-bg text-data-high" },
  attention: {
    label: "Attention",
    Icon: AlertTriangle,
    className: "bg-data-info-bg text-data-info",
  },
};

/* ------------------------------- Page ------------------------------- */

export default function Home() {
  const router = useRouter();
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const [summaryData, analysesData] = await Promise.all([
        api.getPortfolioSummary(),
        api.listAnalyses().catch(() => [] as AnalysisSummary[]),
      ]);
      setSummary(summaryData);
      setAnalyses(analysesData);
    } catch {
      // Retry once — Safari aborts in-flight fetches on back-navigation.
      try {
        setSummary(await api.getPortfolioSummary());
      } catch {
        setError(true);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    chatApi
      .listThreads()
      .then((t) =>
        setThreads(
          [...t]
            .sort(
              (a, b) =>
                new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
            )
            .slice(0, 5),
        ),
      )
      .catch(() => setThreads([]));
  }, []);

  const askAssistant = useCallback(
    (message?: string) => {
      router.push(message ? `/chat?message=${encodeURIComponent(message)}` : "/chat");
    },
    [router],
  );

  const kpiTiles: KpiTileData[] = useMemo(() => {
    if (!summary) return [];
    const approved =
      (summary.counts_by_status?.approved ?? 0) +
      (summary.counts_by_status?.published ?? 0);
    return [
      {
        label: "Portfolio footprint",
        value: compactNumber(summary.total_kg_co2e),
        unit: "kg CO₂e",
      },
      {
        label: "Primary data share",
        value: compactNumber((summary.avg_primary_data_share ?? 0) * 100),
        unit: "%",
        bar: summary.avg_primary_data_share ?? 0,
      },
      {
        label: "Open flags",
        value: compactNumber(summary.open_flags_count),
        unit: "products",
        hint: `${summary.needs_attention_count ?? 0} need attention`,
      },
      {
        label: "Approved & published",
        value: compactNumber(approved),
        unit: `of ${summary.product_count}`,
      },
    ];
  }, [summary]);

  const attention = useMemo(
    () =>
      analyses
        .map(toAttentionItem)
        .filter((x): x is AttentionItem => x !== null)
        .sort((a, b) => b.severity - a.severity)
        .slice(0, 6),
    [analyses],
  );

  return (
    <div className="mx-auto w-full max-w-[1200px] space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
            {new Date().toLocaleDateString("en", {
              weekday: "long",
              month: "long",
              day: "numeric",
            })}
          </div>
          <h1 className="mt-1 text-h1 font-semibold text-foreground">{greeting()}</h1>
          <p className="mt-1 max-w-xl text-small text-muted-foreground">
            {summary
              ? summary.needs_attention_count && summary.needs_attention_count > 0
                ? `${summary.needs_attention_count} product${summary.needs_attention_count === 1 ? "" : "s"} need your attention. Tracking ${summary.product_count} footprint${summary.product_count === 1 ? "" : "s"}.`
                : `All clear — tracking ${summary.product_count} footprint${summary.product_count === 1 ? "" : "s"}.`
              : "Your Scope 3 command center."}
          </p>
        </div>
        <button
          type="button"
          onClick={() => askAssistant()}
          className="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-small font-medium text-primary-foreground shadow-xs transition-colors hover:bg-primary/90"
        >
          <Sparkles className="h-3.5 w-3.5" />
          Ask the assistant
        </button>
      </div>

      {/* KPI strip (real) */}
      {loading && !summary ? (
        <Skeleton className="h-[104px] rounded-lg" />
      ) : error ? (
        <div className="rounded-lg border border-border bg-surface p-4 text-small text-muted-foreground">
          Couldn&apos;t load your portfolio overview.{" "}
          <button
            type="button"
            onClick={() => void load()}
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            Retry
          </button>
        </div>
      ) : summary ? (
        <KpiStrip tiles={kpiTiles} />
      ) : null}

      {/* Two-column body */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        {/* Attention queue (real) */}
        <section className="overflow-hidden rounded-lg border border-border bg-surface shadow-xs lg:col-span-2">
          <header className="flex items-center justify-between border-b border-border bg-surface-2 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <h2 className="text-body font-semibold text-foreground">Needs your attention</h2>
              {attention.length > 0 ? (
                <span className="inline-flex items-center rounded-full bg-data-medium-bg px-1.5 py-0.5 text-caption font-medium text-data-medium">
                  {attention.length} open
                </span>
              ) : null}
            </div>
            <Link
              href="/products?health=attention"
              className="inline-flex items-center gap-1 text-caption font-medium text-primary hover:underline"
            >
              View portfolio <ArrowRight className="h-3 w-3" />
            </Link>
          </header>
          {loading ? (
            <div className="space-y-2 p-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 rounded-md" />
              ))}
            </div>
          ) : attention.length === 0 ? (
            <p className="px-4 py-10 text-center text-small text-muted-foreground">
              Nothing needs attention right now. 🎉
            </p>
          ) : (
            <ul>
              {attention.map((item, i) => (
                <AttentionRow key={item.productId} item={item} last={i === attention.length - 1} />
              ))}
            </ul>
          )}
        </section>

        {/* Right column: trend (placeholder) + status breakdown (real) */}
        <aside className="flex flex-col gap-5">
          <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-xs">
            <header className="border-b border-border bg-surface-2 px-4 py-2.5">
              <h2 className="text-body font-semibold text-foreground">Portfolio trend</h2>
            </header>
            <div className="flex flex-col items-center justify-center gap-1 px-4 py-8 text-center">
              <Activity className="h-5 w-5 text-muted-foreground/40" />
              <p className="text-small text-muted-foreground">
                Trend appears once you have footprints across multiple reporting periods.
              </p>
              <Placeholder label="No historical periods yet" />
            </div>
          </div>

          {summary ? <StatusBreakdown summary={summary} /> : null}
        </aside>
      </div>

      {/* Modules */}
      <section>
        <div className="mb-2 flex items-baseline justify-between">
          <h2 className="text-body font-semibold text-foreground">Modules</h2>
          <span className="text-caption text-muted-foreground">
            Or ask the assistant to run any of these
          </span>
        </div>
        <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {MODULES.map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.name}
                type="button"
                onClick={() => askAssistant(m.message)}
                className="group flex items-center gap-3 bg-surface p-4 text-left transition-colors hover:bg-muted/40"
              >
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-primary/10">
                  <Icon className={cn("h-4 w-4", m.accent)} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-body font-semibold text-foreground">{m.name}</span>
                  <span className="block truncate text-caption text-muted-foreground">
                    {m.desc}
                  </span>
                </span>
                <ArrowRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
              </button>
            );
          })}
        </div>
      </section>

      {/* Recent conversations (real) */}
      {threads.length > 0 ? (
        <section className="overflow-hidden rounded-lg border border-border bg-surface shadow-xs">
          <header className="flex items-center justify-between border-b border-border bg-surface-2 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
              <h2 className="text-body font-semibold text-foreground">Recent conversations</h2>
            </div>
            <Link href="/chat" className="text-caption font-medium text-primary hover:underline">
              View all
            </Link>
          </header>
          <ul className="divide-y divide-border">
            {threads.map((thread) => (
              <li key={thread.thread_id}>
                <Link
                  href={`/chat?thread=${thread.thread_id}`}
                  className="flex items-center justify-between gap-4 px-4 py-2.5 transition-colors hover:bg-muted/40"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-body font-medium text-foreground">
                      {thread.title ?? "New conversation"}
                    </span>
                    <span className="block text-caption text-muted-foreground">
                      {formatRelativeTime(thread.updated_at)}
                    </span>
                  </span>
                  <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function AttentionRow({ item, last }: { item: AttentionItem; last: boolean }) {
  const meta = ATTENTION_META[item.kind];
  const Icon = meta.Icon;
  return (
    <li>
      <Link
        href={`/analyzer/${item.productId}`}
        className={cn(
          "group flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/40",
          !last && "border-b border-border",
        )}
      >
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1 rounded-md px-1.5 py-0.5 text-caption font-medium",
            meta.className,
          )}
        >
          <Icon className="h-2.5 w-2.5" />
          {meta.label}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-body font-medium text-foreground">{item.title}</span>
          <span className="block truncate text-caption text-muted-foreground">{item.meta}</span>
        </span>
        {item.status ? <StatusChip status={item.status} /> : null}
        <span className="num shrink-0 text-caption text-muted-foreground">
          {item.updated ? formatRelativeTime(item.updated) : ""}
        </span>
        <ChevronRight className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      </Link>
    </li>
  );
}

function StatusBreakdown({ summary }: { summary: PortfolioSummary }) {
  const entries = Object.entries(summary.counts_by_status ?? {});
  const total = entries.reduce((s, [, c]) => s + c, 0) || 1;
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-xs">
      <header className="flex items-center justify-between border-b border-border bg-surface-2 px-4 py-2.5">
        <h2 className="text-body font-semibold text-foreground">By status</h2>
        <Link href="/products" className="text-caption font-medium text-primary hover:underline">
          Portfolio
        </Link>
      </header>
      <ul className="divide-y divide-border">
        {entries.length === 0 ? (
          <li className="px-4 py-3 text-caption text-muted-foreground">No footprints yet.</li>
        ) : (
          entries.map(([status, count]) => (
            <li key={status} className="px-4 py-2.5">
              <Link
                href={`/products?status=${encodeURIComponent(status)}`}
                className="block"
              >
                <div className="flex items-center justify-between text-small">
                  <span className="font-medium capitalize text-foreground">
                    {status.replace(/_/g, " ")}
                  </span>
                  <span className="num text-muted-foreground">{count}</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full bg-primary"
                    style={{ width: `${(count / total) * 100}%` }}
                  />
                </div>
              </Link>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
