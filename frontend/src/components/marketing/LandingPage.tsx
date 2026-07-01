"use client";

import Link from "next/link";
import {
  Factory,
  FileSearch,
  Leaf,
  MessageSquare,
  UploadCloud,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

/* ── Brand lockup ─────────────────────────────────────────────────── */
function Wordmark() {
  return (
    <div className="flex items-center gap-2">
      <span
        className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground"
        aria-hidden
      >
        <Leaf className="size-4" />
      </span>
      <span className="text-body font-semibold tracking-tight">
        Carbon Analyzer
      </span>
    </div>
  );
}

/* ── Faux window chrome ───────────────────────────────────────────── */
function ChromeBar() {
  return (
    <div className="flex items-center gap-1.5 border-b bg-muted/50 px-3 py-2">
      <span className="size-2 rounded-full bg-data-high/60" aria-hidden />
      <span className="size-2 rounded-full bg-data-medium/60" aria-hidden />
      <span className="size-2 rounded-full bg-data-low/60" aria-hidden />
    </div>
  );
}

/* ── Workflow snapshot mocks (pure CSS, no images) ────────────────── */
function MockUpload() {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="h-2 w-20 rounded bg-muted-foreground/25" />
        <div className="rounded-full bg-data-medium-bg px-1.5 py-0.5 text-caption font-medium text-data-medium">
          flagged
        </div>
      </div>
      <div className="space-y-1.5">
        <div className="h-2 w-full rounded bg-muted" />
        <div className="h-2 w-11/12 rounded bg-muted" />
        <div className="h-2 w-full rounded border border-data-medium/40 bg-data-medium-bg" />
        <div className="h-2 w-10/12 rounded bg-muted" />
      </div>
    </div>
  );
}

function MockFactors() {
  return (
    <div className="space-y-2">
      {[
        { w: "w-24", tier: "low" as const, pct: "92%" },
        { w: "w-20", tier: "medium" as const, pct: "74%" },
        { w: "w-28", tier: "neutral" as const, pct: "—" },
      ].map((row, i) => (
        <div key={i} className="flex items-center justify-between gap-2">
          <div className={`h-2 ${row.w} rounded bg-muted-foreground/25`} />
          <span
            className={
              row.tier === "low"
                ? "rounded-full bg-data-low-bg px-1.5 py-0.5 text-caption font-medium tabular-nums text-data-low"
                : row.tier === "medium"
                  ? "rounded-full bg-data-medium-bg px-1.5 py-0.5 text-caption font-medium tabular-nums text-data-medium"
                  : "rounded-full bg-data-neutral-bg px-1.5 py-0.5 text-caption font-medium tabular-nums text-data-neutral"
            }
          >
            {row.pct}
          </span>
        </div>
      ))}
    </div>
  );
}

function MockHotspots() {
  return (
    <div className="space-y-3">
      <div className="flex items-baseline justify-between">
        <span className="text-caption text-muted-foreground">Total</span>
        <span className="text-small font-semibold tabular-nums">
          412 kg CO₂e
        </span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full">
        <span className="h-full bg-data-high" style={{ width: "52%" }} />
        <span className="h-full bg-data-medium" style={{ width: "28%" }} />
        <span className="h-full bg-data-low" style={{ width: "20%" }} />
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          <span className="h-2 w-20 rounded bg-muted-foreground/25" />
          <span className="text-caption tabular-nums text-data-high">52%</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="h-2 w-16 rounded bg-muted-foreground/25" />
          <span className="text-caption tabular-nums text-data-medium">
            28%
          </span>
        </div>
      </div>
    </div>
  );
}

function MockSupplier() {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <span className="flex size-6 items-center justify-center rounded-md bg-accent text-accent-foreground">
          <Factory className="size-3.5" aria-hidden />
        </span>
        <div className="h-2 w-24 rounded bg-muted-foreground/25" />
      </div>
      <div className="space-y-1.5 rounded-md border bg-muted/40 p-2">
        <div className="h-2 w-full rounded bg-muted" />
        <div className="h-2 w-10/12 rounded bg-muted" />
        <div className="h-2 w-9/12 rounded bg-muted" />
      </div>
      <div className="flex justify-end">
        <span className="rounded-full bg-data-info-bg px-1.5 py-0.5 text-caption font-medium text-data-info">
          GHG-grounded
        </span>
      </div>
    </div>
  );
}

const SNAPSHOTS = [
  {
    title: "Upload & clean your BOM",
    caption: "Messy rows are normalized and flagged for review.",
    mock: <MockUpload />,
  },
  {
    title: "Match emission factors",
    caption: "Each line maps to a CEDA sector with a confidence score.",
    mock: <MockFactors />,
  },
  {
    title: "See footprint & hotspots",
    caption: "Total kg CO₂e with the biggest contributors ranked.",
    mock: <MockHotspots />,
  },
  {
    title: "Engage the right suppliers",
    caption: "Draft GHG-grounded data requests for your top emitters.",
    mock: <MockSupplier />,
  },
];

const CAPABILITIES = [
  {
    icon: UploadCloud,
    name: "Analyzer",
    job: "Estimate a product's footprint from its BOM.",
  },
  {
    icon: FileSearch,
    name: "Gap Analyzer",
    job: "Find what's missing in your Scope 3 data.",
  },
  {
    icon: Factory,
    name: "Supplier Copilot",
    job: "Engage your highest-impact suppliers first.",
  },
  {
    icon: MessageSquare,
    name: "Advisor",
    job: "Ask anything, grounded in your data and the GHG Protocol.",
  },
];

const TRUST_CHIPS = [
  "Open CEDA 2025",
  "GHG Protocol",
  "Cradle-to-gate",
  "Source-cited",
];

export function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* ── Top bar ──────────────────────────────────────────────── */}
      <header className="border-b">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <Wordmark />
          <Button asChild variant="ghost">
            <Link href="/login">Sign in</Link>
          </Button>
        </div>
      </header>

      <main>
        {/* ── Hero ───────────────────────────────────────────────── */}
        <section className="animate-fade-in mx-auto max-w-5xl px-4 pb-20 pt-20 text-center md:pt-28">
          <p className="text-caption uppercase tracking-wide text-muted-foreground">
            Product-level Scope 3, made auditable
          </p>
          <h1 className="mx-auto mt-4 max-w-3xl text-balance text-h1 md:text-display">
            Turn messy bills of materials into auditable product footprints.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-pretty text-body-lg text-muted-foreground">
            For sustainability and business analysts — estimate a product&apos;s
            Scope 3 Category 1 emissions, find the hotspots, and know exactly
            which suppliers to engage. Every number traceable to its source.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <Link href="/demo">Try the live demo</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </section>

        {/* ── Problem framing ────────────────────────────────────── */}
        <section className="mx-auto max-w-5xl px-4 py-16">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-h2">
              BOM data is messy. Scope 3 shouldn&apos;t be.
            </h2>
            <p className="mt-4 text-body text-muted-foreground">
              Analysts spend days hand-cleaning bills of materials, then hunt
              for emission hotspots across brittle spreadsheets. The result is
              hard to audit and harder to repeat. Category 1 — purchased goods
              and services — deserves a traceable, standard method instead of
              one-off guesswork.
            </p>
          </div>
        </section>

        {/* ── Workflow snapshots ─────────────────────────────────── */}
        <section className="mx-auto max-w-5xl px-4 py-16">
          <h2 className="text-center text-h2">How it works</h2>
          <div className="mt-10 grid gap-6 sm:grid-cols-2">
            {SNAPSHOTS.map((step) => (
              <div key={step.title}>
                <div className="overflow-hidden rounded-lg border bg-card shadow-xs">
                  <ChromeBar />
                  <div className="p-5">{step.mock}</div>
                </div>
                <div className="mt-3">
                  <p className="text-small font-medium">{step.title}</p>
                  <p className="text-caption text-muted-foreground">
                    {step.caption}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Capability grid ────────────────────────────────────── */}
        <section className="mx-auto max-w-5xl px-4 py-16">
          <h2 className="text-center text-h2">One platform, four jobs</h2>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {CAPABILITIES.map(({ icon: Icon, name, job }) => (
              <div
                key={name}
                className="rounded-lg border bg-card p-5 shadow-xs"
              >
                <span className="flex size-9 items-center justify-center rounded-md bg-accent text-accent-foreground">
                  <Icon className="size-4" aria-hidden />
                </span>
                <p className="mt-4 text-small font-medium">{name}</p>
                <p className="mt-1 text-caption text-muted-foreground">{job}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Trust band ─────────────────────────────────────────── */}
        <section className="mx-auto max-w-5xl px-4 py-16">
          <div className="rounded-lg border bg-accent/40 p-6 text-center md:p-8">
            <h3 className="text-h3">Auditable by design</h3>
            <p className="mx-auto mt-3 max-w-2xl text-body text-muted-foreground">
              Every emission factor cites its source — Open CEDA 2025 (a USEEIO
              spend-based model) and the GHG Protocol Corporate Value Chain
              Standard. The methodology is standard, the numbers are traceable,
              and unmatched or low-confidence rows are always flagged for human
              review.
            </p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {TRUST_CHIPS.map((chip) => (
                <Badge key={chip} variant="neutral">
                  {chip}
                </Badge>
              ))}
            </div>
          </div>
        </section>

        {/* ── Final CTA ──────────────────────────────────────────── */}
        <section className="mx-auto max-w-5xl px-4 py-20 text-center">
          <h2 className="text-h2">See it on a real product</h2>
          <div className="mt-6 flex justify-center">
            <Button asChild size="lg">
              <Link href="/demo">Try the live demo</Link>
            </Button>
          </div>
        </section>
      </main>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer className="mx-auto max-w-5xl px-4 pb-10">
        <div className="flex flex-col items-start gap-2 border-t pt-6 text-caption text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <Wordmark />
          <span>Product Carbon Footprint Analyzer</span>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
