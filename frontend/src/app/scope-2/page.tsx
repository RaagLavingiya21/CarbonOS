"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Award,
  Building2,
  Calculator,
  CheckCircle2,
  Circle,
  CircleDashed,
  Clock,
  FileText,
  FileWarning,
  Mail,
  Target,
  TrendingDown,
  Upload,
  Zap,
} from "lucide-react";

import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Card } from "@/components/ui/card";
import {
  BuyerRequest,
  Calculation,
  Coverage,
  Eac,
  LandlordRequest,
  Site,
  Target as ReductionTarget,
  scope2Api,
} from "@/lib/scope2-api";
import { formatKg } from "@/lib/utils";

// The seven Scope 2 tools, kept accessible below the cockpit. Nothing is removed
// by the guided home — these are the same destinations, now also reachable via
// the setup steps and attention items.
const TOOLS = [
  { href: "/scope-2/sites", icon: Building2, title: "Sites & utility data" },
  { href: "/scope-2/import", icon: Upload, title: "Import a bill (PDF/OCR)" },
  { href: "/scope-2/calculate", icon: Calculator, title: "Calculate & report" },
  { href: "/scope-2/eacs", icon: Award, title: "EAC registry" },
  { href: "/scope-2/landlord", icon: Mail, title: "Leased-site data requests" },
  { href: "/scope-2/reports", icon: FileText, title: "Buyer & CDP response" },
  { href: "/scope-2/targets", icon: Target, title: "Reduction targets" },
];

type StepState = "done" | "partial" | "todo";

type AttentionItem = {
  icon: typeof Building2;
  text: string;
  href: string;
  cta: string;
};

/** A settled fetch that degrades to a fallback instead of failing the page. */
async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try {
    return await p;
  } catch {
    return fallback;
  }
}

function landlordOverdueCount(requests: LandlordRequest[]): number {
  const now = Date.now();
  return requests.filter((r) => {
    if (r.responded_at || !r.sent_at) return false;
    const sent = Date.parse(r.sent_at);
    if (Number.isNaN(sent)) return false;
    const dueMs = r.reminder_cadence_days * 24 * 60 * 60 * 1000;
    return now - sent > dueMs;
  }).length;
}

export default function Scope2Page() {
  const [sites, setSites] = useState<Site[] | null>(null);
  const [calcs, setCalcs] = useState<Calculation[] | null>(null);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [eacs, setEacs] = useState<Eac[]>([]);
  const [landlord, setLandlord] = useState<LandlordRequest[]>([]);
  const [buyers, setBuyers] = useState<BuyerRequest[]>([]);
  const [target, setTarget] = useState<ReductionTarget | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      // Core three drive the footprint + coverage. If all reject, the service is
      // unreachable and we surface an error.
      safe<Site[] | null>(scope2Api.listSites(), null),
      safe<Calculation[] | null>(scope2Api.listCalculations(), null),
      safe<Coverage | null>(scope2Api.coverage(), null),
      // Best-effort context for attention + setup. A missing one degrades quietly.
      safe<Eac[]>(scope2Api.listEacs(), []),
      safe<LandlordRequest[]>(scope2Api.listLandlordRequests(), []),
      safe<BuyerRequest[]>(scope2Api.listBuyerRequests(), []),
      safe<ReductionTarget | null>(scope2Api.getActiveTarget(), null),
    ]).then(([s, c, cov, e, ll, b, t]) => {
      if (!mounted) return;
      if (s === null && c === null && cov === null) {
        setError("Couldn't reach the Scope 2 service.");
        return;
      }
      setSites(s ?? []);
      setCalcs(c ?? []);
      setCoverage(cov);
      setEacs(e);
      setLandlord(ll);
      setBuyers(b);
      setTarget(t);
    });
    return () => {
      mounted = false;
    };
  }, []);

  const loading = !error && sites === null;
  const latest = calcs?.[0];

  // Footprint gap: how much the clean-energy contracts pulled market-based below
  // the grid-average location-based number.
  const lb = latest?.location_based_kg_co2e ?? 0;
  const mb = latest?.market_based_kg_co2e ?? 0;
  const gap = lb - mb;
  const mbWidthPct = lb > 0 ? Math.min(Math.max((mb / lb) * 100, 0), 100) : 0;
  const gapWidthPct = gap > 0 ? 100 - mbWidthPct : 0;

  // Needs-attention items, each derived from real data (never invented).
  const attention: AttentionItem[] = [];
  if (coverage && coverage.sites_missing_data > 0) {
    attention.push({
      icon: Building2,
      text: `${coverage.sites_missing_data} site${coverage.sites_missing_data === 1 ? "" : "s"} missing utility data`,
      href: "/scope-2/sites",
      cta: "Add data",
    });
  }
  if (coverage && coverage.estimation_fraction > 0) {
    attention.push({
      icon: TrendingDown,
      text: `${Math.round(coverage.estimation_fraction * 100)}% of energy is estimated, not metered`,
      href: "/scope-2/import",
      cta: "Import bills",
    });
  }
  if (latest?.market_fallback_flagged) {
    attention.push({
      icon: FileWarning,
      text: "Market-based used a grid-average fallback for some sites",
      href: "/scope-2/eacs",
      cta: "Add EACs",
    });
  }
  const llOverdue = landlordOverdueCount(landlord);
  if (llOverdue > 0) {
    attention.push({
      icon: Clock,
      text: `${llOverdue} landlord request${llOverdue === 1 ? "" : "s"} overdue`,
      href: "/scope-2/landlord",
      cta: "Follow up",
    });
  }
  const buyerOverdue = buyers.filter((b) => b.is_overdue).length;
  if (buyerOverdue > 0) {
    attention.push({
      icon: Mail,
      text: `${buyerOverdue} buyer request${buyerOverdue === 1 ? "" : "s"} overdue`,
      href: "/scope-2/reports",
      cta: "Respond",
    });
  }

  // Setup spine — done / partial / todo per step, from real signals.
  const hasSites = (sites?.length ?? 0) > 0;
  const dataStep: StepState = !coverage
    ? "todo"
    : coverage.sites_with_data === 0
      ? "todo"
      : coverage.sites_missing_data === 0
        ? "done"
        : "partial";
  const reportStep: StepState = buyers.some((b) => b.answered_at)
    ? "done"
    : buyers.length > 0
      ? "partial"
      : "todo";
  const steps: { label: string; state: StepState; href: string }[] = [
    { label: "Sites", state: hasSites ? "done" : "todo", href: "/scope-2/sites" },
    { label: "Utility data", state: dataStep, href: "/scope-2/import" },
    {
      label: "Calculate",
      state: (calcs?.length ?? 0) > 0 ? "done" : "todo",
      href: "/scope-2/calculate",
    },
    {
      label: "Clean energy",
      state: eacs.length > 0 ? "done" : "todo",
      href: "/scope-2/eacs",
    },
    { label: "Report", state: reportStep, href: "/scope-2/reports" },
  ];
  const setupPct = Math.round(
    (steps.reduce((sum, s) => sum + (s.state === "done" ? 1 : s.state === "partial" ? 0.5 : 0), 0) /
      steps.length) *
      100,
  );

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
          <Zap className="h-5 w-5" aria-hidden />
        </span>
        <div className="flex-1">
          <h1 className="text-h1 font-semibold">Scope 2 — Grid</h1>
          <p className="text-small text-muted-foreground">
            Your Scope 2 system of record for multi-site consumer brands.
          </p>
        </div>
        {latest ? (
          <span className="text-small text-muted-foreground">
            Reporting year {latest.reporting_year}
          </span>
        ) : null}
      </header>

      {error ? (
        <ErrorState title="Couldn't reach the Scope 2 service" message={error} />
      ) : loading ? (
        <div className="space-y-4">
          <Skeleton className="h-[168px] w-full rounded-xl" />
          <Skeleton className="h-[120px] w-full rounded-xl" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Footprint */}
          <Card className="p-5">
            {latest ? (
              <>
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
                    Your footprint
                  </span>
                  <Link
                    href="/scope-2/calculate"
                    className="inline-flex items-center gap-1 text-caption text-muted-foreground hover:text-foreground"
                  >
                    View breakdown <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
                <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2">
                  <div>
                    <div className="flex items-baseline gap-1.5">
                      <span className="tabular-nums text-h1 font-semibold leading-none">
                        {formatKg(mb)}
                      </span>
                    </div>
                    <p className="mt-1 text-caption text-muted-foreground">
                      Market-based — what you report
                    </p>
                  </div>
                  <div className="text-muted-foreground">
                    <span className="tabular-nums text-h3 font-medium leading-none">
                      {formatKg(lb)}
                    </span>
                    <p className="mt-1 text-caption">Location-based — grid average</p>
                  </div>
                </div>

                {/* Gap bar: market-based residual vs. what clean-energy contracts cut. */}
                <div className="mt-4 flex h-3.5 overflow-hidden rounded border border-border">
                  <div className="bg-data-low/80" style={{ width: `${mbWidthPct}%` }} />
                  <div className="bg-data-low-bg" style={{ width: `${gapWidthPct}%` }} />
                </div>
                <p className="mt-2 text-caption text-muted-foreground">
                  {gap > 0 ? (
                    <>
                      <span className="text-data-low">■</span> {formatKg(mb)} you still emit
                      &nbsp;·&nbsp; <span className="text-data-low/50">■</span> {formatKg(gap)} cut
                      by your RECs &amp; PPAs
                    </>
                  ) : (
                    <>
                      Market-based is at or above the grid average — add contractual instruments
                      (RECs/PPAs) on the EAC registry to open a reduction gap.
                    </>
                  )}
                </p>
                <p className="mt-3 text-caption text-muted-foreground">
                  {latest.consumption_mwh != null
                    ? `${latest.consumption_mwh.toFixed(1)} MWh · `
                    : ""}
                  location-based and market-based are always reported separately, never merged.
                </p>
              </>
            ) : (
              <div className="py-4 text-center">
                <p className="text-h3 font-medium">No footprint yet</p>
                <p className="mx-auto mt-1 max-w-md text-small text-muted-foreground">
                  Add your sites and import utility data, then run your first dual-method
                  calculation. The steps below walk you through it.
                </p>
                <Link
                  href={hasSites ? "/scope-2/import" : "/scope-2/sites"}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-small font-medium text-primary-foreground transition-opacity hover:opacity-90"
                >
                  {hasSites ? "Import utility data" : "Add your first site"}
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            )}
          </Card>

          {/* Needs attention */}
          <Card className="p-5">
            <span className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
              Needs your attention
              {attention.length > 0 ? ` (${attention.length})` : ""}
            </span>
            {attention.length === 0 ? (
              <div className="mt-3 flex items-center gap-2 text-small text-muted-foreground">
                <CheckCircle2 className="h-4 w-4 text-data-low" />
                You&apos;re all caught up — nothing needs review right now.
              </div>
            ) : (
              <ul className="mt-3 space-y-2">
                {attention.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <li key={i}>
                      <Link
                        href={item.href}
                        className="group flex items-center gap-2.5 rounded-md border border-border px-3 py-2 text-small transition-colors hover:border-border-strong hover:bg-secondary/40"
                      >
                        <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="flex-1">{item.text}</span>
                        <span className="inline-flex items-center gap-1 text-caption font-medium text-primary">
                          {item.cta}
                          <ArrowRight className="h-3 w-3 -translate-x-0.5 opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100" />
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>

          {/* Setup progress */}
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
                Setup progress
              </span>
              <span className="text-small font-medium tabular-nums">{setupPct}%</span>
            </div>
            <div className="grid grid-cols-5 gap-2">
              {steps.map((step) => {
                const Icon =
                  step.state === "done"
                    ? CheckCircle2
                    : step.state === "partial"
                      ? CircleDashed
                      : Circle;
                const tone =
                  step.state === "done"
                    ? "text-data-low"
                    : step.state === "partial"
                      ? "text-data-medium"
                      : "text-muted-foreground";
                return (
                  <Link
                    key={step.label}
                    href={step.href}
                    className="flex flex-col items-center gap-1.5 rounded-md py-2 text-center transition-colors hover:bg-secondary/40"
                  >
                    <Icon className={`h-5 w-5 ${tone}`} />
                    <span className="text-caption text-muted-foreground">{step.label}</span>
                  </Link>
                );
              })}
            </div>
            {target ? (
              <p className="mt-3 flex items-center gap-1.5 text-caption text-muted-foreground">
                <Target className="h-3 w-3" />
                Active reduction target: {target.target_year} vs. {target.base_year} base year.
              </p>
            ) : null}
          </Card>

          {/* All tools */}
          <div>
            <p className="mb-3 text-caption font-medium uppercase tracking-wide text-muted-foreground">
              All tools
            </p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {TOOLS.map((tool) => {
                const Icon = tool.icon;
                return (
                  <Link key={tool.href} href={tool.href} className="group">
                    <Card className="flex h-full items-center gap-3 p-3 transition-colors duration-micro ease-out hover:border-border-strong">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="flex-1 text-small font-medium">{tool.title}</span>
                      <ArrowRight className="h-3.5 w-3.5 -translate-x-1 text-muted-foreground opacity-0 transition-all duration-micro group-hover:translate-x-0 group-hover:opacity-100" />
                    </Card>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
