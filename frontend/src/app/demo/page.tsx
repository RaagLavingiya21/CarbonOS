"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  Leaf,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { BreakdownTable, type BreakdownRow } from "@/components/data/BreakdownTable";
import { ConfidenceBadge } from "@/components/data/ConfidenceBadge";
import { HotspotBar } from "@/components/data/HotspotBar";
import { MetricCard } from "@/components/data/MetricCard";
import { SourceCitation } from "@/components/data/SourceCitation";
import { Term } from "@/components/data/Term";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

// ── Seeded static data (no backend) ──────────────────────────────────────────

const PRODUCT_NAME = "Insulated water bottle";
const TOTAL_KG_CO2E = "22.30";
const MATCHED_ITEMS = 5;
const FLAGGED_ITEMS = 1;

interface BomRow {
  component: string;
  material: string;
  quantity: string;
  spend: string;
  flag?: { label: string; variant: "high" | "medium" | "neutral" };
}

const BOM_ROWS: BomRow[] = [
  { component: "Bottle body", material: "Stainless steel", quantity: "0.32 kg", spend: "$6.50" },
  {
    component: "Powder coating",
    material: "Coating",
    quantity: "0.05 kg",
    spend: "—",
    flag: { label: "missing spend — flagged", variant: "high" },
  },
  {
    component: "Silicone seal",
    material: "Silicone",
    quantity: "0.23 kg",
    spend: "$0.40",
    flag: { label: "converted 8 oz → 0.23 kg", variant: "medium" },
  },
  { component: "Cap", material: "LDPE", quantity: "0.04 kg", spend: "$0.30" },
  {
    component: "Cap (liner)",
    material: "LDPE",
    quantity: "0.04 kg",
    spend: "$0.30",
    flag: { label: "possible duplicate", variant: "neutral" },
  },
  { component: "Packaging", material: "Cardboard", quantity: "0.06 kg", spend: "$0.25" },
];

interface MatchRow {
  material: string;
  sector: string;
  source: string;
  confidence: number | null;
}

const MATCH_ROWS: MatchRow[] = [
  {
    material: "Stainless steel",
    sector: "Iron and steel mills and ferroalloy manufacturing",
    source: "Open CEDA 2025, Iron and steel mills, USA",
    confidence: 100,
  },
  {
    material: "Coating",
    sector: "Paint and coating manufacturing",
    source: "Open CEDA 2025, Paint and coating, USA",
    confidence: 88,
  },
  {
    material: "Silicone",
    sector: "Other basic organic chemical manufacturing",
    source: "Open CEDA 2025, Other basic organic chemicals, USA",
    confidence: 74,
  },
  {
    material: "LDPE",
    sector: "Plastics material and resin manufacturing",
    source: "Open CEDA 2025, Plastics & resin, USA",
    confidence: 91,
  },
  {
    material: "Cardboard",
    sector: "Paperboard container manufacturing",
    source: "Open CEDA 2025, Paperboard containers, USA",
    confidence: 95,
  },
];

const BREAKDOWN_ROWS: BreakdownRow[] = [
  {
    rowIndex: 1,
    component: "Bottle body",
    material: "Stainless steel",
    spendUsd: 6.5,
    sector: "Iron and steel mills and ferroalloy manufacturing",
    efSource: "Open CEDA 2025, Iron and steel mills, USA",
    confidence: 100,
    kgCo2e: 9.4,
    sharePct: 42.1,
  },
  {
    rowIndex: 2,
    component: "Powder coating",
    material: "Coating",
    spendUsd: 1.2,
    sector: "Paint and coating manufacturing",
    efSource: "Open CEDA 2025, Paint and coating, USA",
    confidence: 88,
    kgCo2e: 6.1,
    sharePct: 27.3,
  },
  {
    rowIndex: 3,
    component: "Silicone seal",
    material: "Silicone",
    spendUsd: 0.4,
    sector: "Other basic organic chemical manufacturing",
    efSource: "Open CEDA 2025, Other basic organic chemicals, USA",
    confidence: 74,
    kgCo2e: 3.2,
    sharePct: 14.3,
  },
  {
    rowIndex: 4,
    component: "Cap",
    material: "LDPE",
    spendUsd: 0.3,
    sector: "Plastics material and resin manufacturing",
    efSource: "Open CEDA 2025, Plastics & resin, USA",
    confidence: 91,
    kgCo2e: 2.6,
    sharePct: 11.7,
  },
  {
    rowIndex: 5,
    component: "Packaging",
    material: "Cardboard",
    spendUsd: 0.25,
    sector: "Paperboard container manufacturing",
    efSource: "Open CEDA 2025, Paperboard containers, USA",
    confidence: 95,
    kgCo2e: 1.0,
    sharePct: 4.6,
  },
];

interface Hotspot {
  label: string;
  sublabel: string;
  sharePct: number;
  value: string;
  emphasized?: boolean;
}

const HOTSPOTS: Hotspot[] = [
  { label: "Bottle body", sublabel: "stainless steel", sharePct: 42.1, value: "9.40 kg", emphasized: true },
  { label: "Powder coating", sublabel: "coating", sharePct: 27.3, value: "6.10 kg" },
  { label: "Silicone seal", sublabel: "silicone", sharePct: 14.3, value: "3.20 kg" },
  { label: "Cap", sublabel: "LDPE", sharePct: 11.7, value: "2.60 kg" },
  { label: "Packaging", sublabel: "cardboard", sharePct: 4.6, value: "1.00 kg" },
];

// ── Stepper config ───────────────────────────────────────────────────────────

const STEPS = [
  { id: 1, title: "Clean the BOM" },
  { id: 2, title: "Match factors" },
  { id: 3, title: "Footprint" },
  { id: 4, title: "Engage suppliers" },
] as const;

export default function DemoPage() {
  const [step, setStep] = useState(1);
  const totalSteps = STEPS.length;

  const goNext = () => setStep((s) => Math.min(totalSteps, s + 1));
  const goBack = () => setStep((s) => Math.max(1, s - 1));

  return (
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <header className="border-b">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Leaf className="h-4 w-4" aria-hidden />
            </span>
            <span className="text-body font-display font-semibold">Carbon Analyzer</span>
            <Badge variant="neutral">Demo · sample data</Badge>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/">Exit demo</Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8">
        {/* Stepper */}
        <div className="mb-8">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
              Step {step} of {totalSteps}
            </p>
            <p className="text-caption text-muted-foreground">{PRODUCT_NAME}</p>
          </div>
          <div className="flex gap-1.5">
            {STEPS.map((s) => (
              <div key={s.id} className="flex flex-1 flex-col gap-1.5">
                <div
                  className={cn(
                    "h-1 rounded-full transition-colors duration-200",
                    s.id <= step ? "bg-primary" : "bg-muted",
                  )}
                />
                <span
                  className={cn(
                    "text-caption",
                    s.id === step ? "font-medium text-foreground" : "text-muted-foreground",
                  )}
                >
                  {s.title}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Step content */}
        <div key={step} className="animate-fade-in">
          {step === 1 && <StepClean />}
          {step === 2 && <StepMatch />}
          {step === 3 && <StepFootprint />}
          {step === 4 && <StepEngage />}
        </div>

        {/* Nav */}
        <div className="mt-8 flex items-center justify-between">
          <Button variant="outline" onClick={goBack} disabled={step === 1}>
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Back
          </Button>
          {step < totalSteps ? (
            <Button onClick={goNext}>
              Next
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Button>
          ) : (
            <Button asChild>
              <Link href="/signup">
                Create your workspace
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </Button>
          )}
        </div>

        {/* Closing CTA — shown on the final step */}
        {step === totalSteps && (
          <Card className="mt-10 animate-slide-up bg-accent/40 p-8 text-center">
            <h2 className="text-h2">Ready to analyze your own products?</h2>
            <p className="mx-auto mt-2 max-w-md text-body text-muted-foreground">
              Upload your bill of materials and get an auditable, source-cited footprint in
              minutes — with every number traceable.
            </p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              <Button size="lg" asChild>
                <Link href="/signup">Create your workspace</Link>
              </Button>
              <Button size="lg" variant="ghost" asChild>
                <Link href="/login">Sign in</Link>
              </Button>
            </div>
          </Card>
        )}
      </main>
    </div>
  );
}

// ── Reusable step header ──────────────────────────────────────────────────────

function StepHeading({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-6">
      <h1 className="text-h1 text-balance">{title}</h1>
      <p className="mt-2 text-body-lg text-muted-foreground text-pretty">{children}</p>
    </div>
  );
}

// ── Step 1 — Clean the BOM ────────────────────────────────────────────────────

function StepClean() {
  return (
    <section>
      <StepHeading title="We parsed and cleaned your bill of materials.">
        Messy rows are normalized — imperial units converted, formatting fixed — and anything
        ambiguous is flagged for human review rather than guessed.
      </StepHeading>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full border-collapse text-small">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-caption uppercase tracking-wide text-muted-foreground">
              <th className="px-3 py-2 font-medium">Component</th>
              <th className="px-3 py-2 font-medium">Material</th>
              <th className="px-3 py-2 text-right font-medium">Quantity</th>
              <th className="px-3 py-2 text-right font-medium">Spend</th>
              <th className="px-3 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {BOM_ROWS.map((row, i) => (
              <tr key={i} className="border-b last:border-0 align-middle">
                <td className="px-3 py-2.5 font-medium">{row.component}</td>
                <td className="px-3 py-2.5 text-muted-foreground">{row.material}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">{row.quantity}</td>
                <td className="px-3 py-2.5 text-right tabular-nums">{row.spend}</td>
                <td className="px-3 py-2.5">
                  {row.flag ? (
                    <Badge variant={row.flag.variant}>{row.flag.label}</Badge>
                  ) : (
                    <span className="text-caption text-muted-foreground">clean</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ── Step 2 — Match emission factors ───────────────────────────────────────────

function StepMatch() {
  return (
    <section>
      <StepHeading title="Each line is matched to a CEDA sector with a confidence score.">
        Every <Term name="emission factor">emission factor</Term> carries a source citation and a
        match confidence, so you can trust — or challenge — each number.
      </StepHeading>

      <div className="overflow-x-auto rounded-lg border">
        <table className="w-full border-collapse text-small">
          <thead>
            <tr className="border-b bg-muted/40 text-left text-caption uppercase tracking-wide text-muted-foreground">
              <th className="px-3 py-2 font-medium">Material</th>
              <th className="px-3 py-2 font-medium">Matched sector</th>
              <th className="px-3 py-2 font-medium">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {MATCH_ROWS.map((row, i) => (
              <tr key={i} className="border-b last:border-0 align-top">
                <td className="px-3 py-2.5 font-medium">{row.material}</td>
                <td className="px-3 py-2.5">
                  <div className="max-w-[18rem]">{row.sector}</div>
                  <SourceCitation source={row.source} className="mt-0.5" />
                </td>
                <td className="px-3 py-2.5">
                  <ConfidenceBadge score={row.confidence} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Alert className="mt-4">
        <AlertDescription>
          1 row couldn&apos;t be matched and is excluded from the total — flagged for review.
        </AlertDescription>
      </Alert>
    </section>
  );
}

// ── Step 3 — Footprint & hotspots ─────────────────────────────────────────────

function StepFootprint() {
  return (
    <section>
      <StepHeading title="Here's the product's footprint and where the emissions concentrate.">
        One headline number, broken down by component so the hotspots — and your reduction
        priorities — are obvious at a glance.
      </StepHeading>

      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCard
          label="Total footprint"
          value={TOTAL_KG_CO2E}
          unit="kg CO₂e"
          hint={
            <>
              <Term name="scope 3">Scope 3</Term> · <Term name="cradle-to-gate">cradle-to-gate</Term>
            </>
          }
        />
        <MetricCard label="Matched items" value={MATCHED_ITEMS} />
        <MetricCard label="Flagged items" value={FLAGGED_ITEMS} />
      </div>

      <Card className="mt-6 p-5">
        <h3 className="mb-4 text-h3">Emission hotspots</h3>
        <div className="flex flex-col gap-4">
          {HOTSPOTS.map((h) => (
            <HotspotBar
              key={h.label}
              label={h.label}
              sublabel={h.sublabel}
              sharePct={h.sharePct}
              value={h.value}
              emphasized={h.emphasized}
            />
          ))}
        </div>
      </Card>

      <div className="mt-6">
        <h3 className="mb-3 text-h3">Auditable breakdown</h3>
        <BreakdownTable rows={BREAKDOWN_ROWS} />
      </div>
    </section>
  );
}

// ── Step 4 — Engage suppliers ─────────────────────────────────────────────────

function StepEngage() {
  return (
    <section>
      <StepHeading title="Start with your highest-impact suppliers.">
        Outreach is ranked by emissions and grounded in the GHG Protocol, so you ask the right
        suppliers for the right primary data first.
      </StepHeading>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
              #1 emitter
            </span>
            <Badge variant="high">42.1% of total</Badge>
          </div>
          <p className="mt-1 text-body font-medium">Bottle body</p>
          <p className="text-small text-muted-foreground">
            Stainless steel · <span className="tabular-nums">9.40 kg CO₂e</span>
          </p>
        </Card>
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <span className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
              #2 emitter
            </span>
            <Badge variant="medium">27.3% of total</Badge>
          </div>
          <p className="mt-1 text-body font-medium">Powder coating</p>
          <p className="text-small text-muted-foreground">
            Coating · <span className="tabular-nums">6.10 kg CO₂e</span>
          </p>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Mail className="h-4 w-4 text-muted-foreground" aria-hidden />
            <CardTitle>Drafted supplier outreach</CardTitle>
          </div>
          <CardDescription>
            Sample request for primary emissions data on the stainless steel bottle body.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border bg-muted/30 p-4 text-small leading-relaxed">
            <p className="font-medium">Subject: Primary emissions data — stainless steel bottle body</p>
            <p className="mt-3">Hi team,</p>
            <p className="mt-2 text-muted-foreground">
              As part of our Scope 3 Category 1 (purchased goods) assessment, the stainless steel
              bottle body you supply is the single largest contributor to this product&apos;s
              cradle-to-gate footprint (~9.40 kg CO₂e, 42% of the total).
            </p>
            <p className="mt-2 text-muted-foreground">
              To replace our secondary (industry-average) estimate with supplier-specific data,
              could you share a product carbon footprint or facility-level emission factor for this
              part, following the GHG Protocol Product Standard? Even a cradle-to-gate figure per kg
              would let us refine the estimate.
            </p>
            <p className="mt-2 text-muted-foreground">Happy to send our template. Thank you,</p>
            <p className="mt-2 text-muted-foreground">Sustainability Analytics</p>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-caption text-muted-foreground">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
            Grounded in the GHG Protocol Product Standard
          </div>
        </CardContent>
      </Card>

      <div className="mt-6 flex items-center gap-1.5 text-caption text-muted-foreground">
        <Sparkles className="h-3.5 w-3.5" aria-hidden />
        This is a guided demo on seeded sample data — no data leaves your browser.
      </div>
    </section>
  );
}
