"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ChevronRight, Flag } from "lucide-react";

import { AnalyzerPageContent } from "@/app/analyzer/page";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { AnalysisSummary, PortfolioSummary, api } from "@/lib/api";
import { cn, formatRelativeTime } from "@/lib/utils";
import { AnalyzeQuickStart } from "@/components/portfolio/AnalyzeQuickStart";
import { KpiStrip, type KpiTileData } from "@/components/portfolio/KpiStrip";
import { FilterChip, SegmentedControl } from "@/components/portfolio/FilterChip";
import { StatusChip } from "@/components/portfolio/StatusChip";
import { Placeholder } from "@/components/portfolio/Placeholder";
import {
  Cell,
  GroupHead,
  HeadCell,
  PctBar,
  SortHead,
} from "@/components/portfolio/DataTable";

// One template shared by grouped header, column header, and every row.
const GRID =
  "grid-cols-[minmax(260px,2fr)_110px_64px_120px_72px_100px_150px_96px_80px_110px_44px]";

function compactNumber(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "0";
  return new Intl.NumberFormat("en", {
    maximumFractionDigits: value >= 100 ? 0 : 1,
  }).format(value);
}

function aggregateDqr(a: AnalysisSummary): number | null {
  const values = [a.technological_dqr, a.geographical_dqr, a.temporal_dqr].filter(
    (v): v is number => typeof v === "number",
  );
  if (values.length === 0) return null;
  return values.reduce((s, v) => s + v, 0) / values.length;
}

const STATUS_ORDER = ["draft", "calculated", "under_review", "approved", "published", "flagged"];

function ProductsPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get("status");
  const healthFilter = searchParams.get("health");

  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Analyzer is folded into Portfolio: the quick-start opens the full analyze
  // flow inline here instead of navigating to a separate page.
  const [analyzeMode, setAnalyzeMode] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rows, portfolioSummary] = await Promise.all([
        api.listAnalyses({
          status: statusFilter ?? undefined,
          health: healthFilter ?? undefined,
        }),
        api.getPortfolioSummary().catch(() => null),
      ]);
      setAnalyses(rows);
      setSummary(portfolioSummary);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, healthFilter]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const kpiTiles: KpiTileData[] = useMemo(() => {
    if (!summary) return [];
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
        unit: "line items",
        hint: `${summary.needs_attention_count ?? 0} products need attention`,
      },
      {
        label: "Products tracked",
        value: compactNumber(summary.product_count),
        unit: "footprints",
      },
    ];
  }, [summary]);

  const statusFilters = useMemo(() => {
    const counts = summary?.counts_by_status ?? {};
    const present = STATUS_ORDER.filter((s) => s in counts);
    const extras = Object.keys(counts).filter((s) => !STATUS_ORDER.includes(s));
    return [...present, ...extras];
  }, [summary]);

  if (analyzeMode) {
    return (
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => setAnalyzeMode(false)}
          className="-ml-1 inline-flex items-center gap-1.5 text-small font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to portfolio
        </button>
        <Suspense fallback={null}>
          <AnalyzerPageContent />
        </Suspense>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Page header */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
            Screening-grade · Open CEDA 2025
          </div>
          <h1 className="mt-1 text-h1 font-semibold text-foreground">Product portfolio</h1>
          <p className="mt-1 max-w-xl text-small text-muted-foreground">
            {summary ? `${summary.product_count} products. ` : ""}
            Click any row for line items, hotspots, and source citations.
          </p>
        </div>
      </div>

      {/* KPI strip (real portfolio aggregates) */}
      {summary ? (
        <KpiStrip tiles={kpiTiles} />
      ) : loading ? (
        <Skeleton className="h-[104px] rounded-lg" />
      ) : null}

      {/* Analyzer quick-start (folded in from the old standalone module) */}
      <AnalyzeQuickStart onStart={() => setAnalyzeMode(true)} />

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-1.5">
        <FilterChip
          label="Status"
          value="All"
          active={!statusFilter}
          href="/products"
        />
        {statusFilters.map((s) => (
          <FilterChip
            key={s}
            label={s.replace(/_/g, " ")}
            value={String(summary?.counts_by_status?.[s] ?? 0)}
            active={statusFilter === s}
            href={`/products?status=${encodeURIComponent(s)}`}
          />
        ))}
        {healthFilter ? (
          <FilterChip label="Health" value={healthFilter} active href="/products" />
        ) : null}

        <div className="ml-auto">
          <SegmentedControl
            value="table"
            options={[
              { value: "table", label: "Table" },
              { value: "board", label: "Board", disabled: true },
              { value: "chart", label: "Chart", disabled: true },
            ]}
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-lg border border-border bg-surface shadow-xs">
        {loading ? (
          <div className="space-y-2 p-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-11 rounded-md" />
            ))}
          </div>
        ) : error ? (
          <div className="p-4">
            <ErrorState
              title="Couldn't load portfolio"
              message={error}
              onRetry={() => void loadData()}
            />
          </div>
        ) : analyses.length === 0 ? (
          <p className="py-10 text-center text-small text-muted-foreground">
            No saved products{statusFilter ? ` with status "${statusFilter}"` : ""} yet. Use
            “Analyze new BOM” above to create your first footprint.
          </p>
        ) : (
          <div className="relative">
            <div className="overflow-x-auto">
              <div className="min-w-[1200px]">
                {/* Grouped header */}
                <div
                  className={cn(
                    "grid",
                    GRID,
                    "border-b border-border/70 bg-surface-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground/80",
                  )}
                >
                  <GroupHead label="Product" sticky />
                  <GroupHead label="Lifecycle" span={2} />
                  <GroupHead label="Footprint" span={3} align="right" />
                  <GroupHead label="Data quality" span={3} />
                  <GroupHead label="Activity" />
                  <GroupHead label="" />
                </div>

                {/* Column header */}
                <div
                  className={cn(
                    "grid",
                    GRID,
                    "border-b border-border bg-surface-2 text-caption font-medium uppercase tracking-wide text-muted-foreground",
                  )}
                >
                  <HeadCell sticky>
                    <SortHead label="Product" />
                  </HeadCell>
                  <HeadCell>
                    <SortHead label="Status" />
                  </HeadCell>
                  <HeadCell>
                    <SortHead label="Ver." />
                  </HeadCell>
                  <HeadCell align="right">
                    <SortHead label="kg CO₂e" numeric />
                  </HeadCell>
                  <HeadCell align="right">
                    <SortHead label="Δ" numeric />
                  </HeadCell>
                  <HeadCell>
                    <SortHead label="Declared" />
                  </HeadCell>
                  <HeadCell>
                    <SortHead label="Primary data" />
                  </HeadCell>
                  <HeadCell>
                    <SortHead label="DQR" />
                  </HeadCell>
                  <HeadCell align="right">
                    <SortHead label="Flagged" numeric />
                  </HeadCell>
                  <HeadCell>
                    <SortHead label="Updated" />
                  </HeadCell>
                  <HeadCell> </HeadCell>
                </div>

                {/* Rows */}
                {analyses.map((a) => (
                  <ProductRow key={a.product_id} a={a} onOpen={() => router.push(`/analyzer/${a.product_id}`)} />
                ))}
              </div>
            </div>
            <div className="pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l from-surface to-transparent" />
          </div>
        )}

        {!loading && !error && analyses.length > 0 ? (
          <div className="flex items-center justify-between border-t border-border bg-surface-2 px-4 py-2 text-caption text-muted-foreground">
            <div>
              Showing <span className="num text-foreground">{analyses.length}</span>
              {summary ? (
                <>
                  {" "}
                  of <span className="num text-foreground">{summary.product_count}</span>
                </>
              ) : null}{" "}
              products
            </div>
            <div className="flex items-center gap-2">
              <span>Open</span>
              <span className="kbd">↵</span>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ProductRow({ a, onOpen }: { a: AnalysisSummary; onOpen: () => void }) {
  const pds = a.primary_data_share ?? 0;
  const dqr = aggregateDqr(a);
  const dqrTone =
    dqr === null
      ? ""
      : dqr <= 2
        ? "text-data-low"
        : dqr <= 3
          ? "text-data-medium"
          : "text-data-high";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpen();
        }
      }}
      className={cn(
        "group grid h-11 cursor-pointer border-b border-border text-body transition-colors hover:bg-muted/60 focus:outline-none focus-visible:bg-muted/60",
        GRID,
      )}
    >
      {/* Product (sticky) */}
      <Cell sticky>
        <div className="flex min-w-0 items-center gap-2.5">
          <div className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-muted text-[10px] font-semibold text-muted-foreground">
            {(a.product_name || "?").charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="truncate font-medium text-foreground">{a.product_name}</span>
              <span className="num shrink-0 text-caption text-muted-foreground">
                #{a.product_id}
              </span>
            </div>
            <div className="truncate text-caption text-muted-foreground">
              {a.matched_items} matched line items
            </div>
          </div>
        </div>
      </Cell>

      {/* Status */}
      <Cell>
        <StatusChip status={a.status} />
      </Cell>

      {/* Version */}
      <Cell>
        <span className="num text-small font-medium text-foreground">v{a.version ?? 1}</span>
      </Cell>

      {/* Total */}
      <Cell align="right">
        <span className="num text-body font-semibold text-foreground">
          {compactNumber(a.total_kg_co2e)}
        </span>
      </Cell>

      {/* Delta — no prior-period source */}
      <Cell align="right">
        <Placeholder label="No prior-period comparison yet" />
      </Cell>

      {/* Declared unit */}
      <Cell>
        {a.declared_unit ? (
          <span className="num text-caption text-muted-foreground">{a.declared_unit}</span>
        ) : (
          <Placeholder label="No declared unit set" />
        )}
      </Cell>

      {/* Primary data share */}
      <Cell>
        <PctBar value={pds} />
      </Cell>

      {/* Data quality (aggregate DQR) */}
      <Cell>
        {dqr === null ? (
          <Placeholder label="No DQR scored yet" />
        ) : (
          <span className={cn("num text-small font-medium", dqrTone)} title="Aggregate DQR (lower is better)">
            {dqr.toFixed(1)}
          </span>
        )}
      </Cell>

      {/* Flagged */}
      <Cell align="right">
        {a.flagged_items > 0 ? (
          <span className="inline-flex items-center gap-1 text-small font-medium text-data-medium">
            <Flag className="h-3 w-3" />
            <span className="num">{a.flagged_items}</span>
          </span>
        ) : (
          <span className="num text-small text-muted-foreground">0</span>
        )}
      </Cell>

      {/* Updated */}
      <Cell>
        <span className="text-caption text-muted-foreground">
          {a.analysis_date ? formatRelativeTime(a.analysis_date) : <Placeholder />}
        </span>
      </Cell>

      {/* Actions */}
      <Cell>
        <span className="grid h-6 w-6 place-items-center rounded text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100">
          <ChevronRight className="h-3.5 w-3.5" />
        </span>
      </Cell>
    </div>
  );
}

export default function ProductsPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-3">
          <Skeleton className="h-[104px] rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      }
    >
      <ProductsPageContent />
    </Suspense>
  );
}
