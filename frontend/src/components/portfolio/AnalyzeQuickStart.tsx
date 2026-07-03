"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowRight,
  FileSpreadsheet,
  Plus,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Wand2,
  X,
} from "lucide-react";

const EXPECTED_COLUMNS = ["component", "material", "quantity", "spend_usd"];
const STEPS = [
  "Parse & clean the uploaded BOM",
  "Match each line to an emission factor",
  "Calculate footprint & rank hotspots",
];

/**
 * Portfolio entry point for the BOM analyzer (folded in from the old standalone
 * Analyzer nav item). Compact by default; expands to explain the flow. Every CTA
 * routes into the live `/analyzer` workflow — no fake upload happens here.
 */
export function AnalyzeQuickStart() {
  const [open, setOpen] = useState(false);

  return (
    <section className="relative overflow-hidden rounded-lg border border-border bg-surface shadow-xs">
      {!open ? (
        <div className="flex flex-wrap items-center justify-between gap-4 px-4 py-2.5">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/[0.08] px-2 py-0.5 text-caption font-semibold uppercase tracking-wide text-primary">
              <Wand2 className="h-3 w-3" />
              Analyzer
            </span>
            <div>
              <h2 className="text-body font-semibold text-foreground">
                Analyze a new bill of materials
              </h2>
              <p className="text-caption text-muted-foreground">
                Parse a CSV, match factors, and surface hotspots — every assumption reviewable.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-small font-semibold text-primary-foreground shadow-xs transition-colors hover:bg-primary/90"
          >
            <Plus className="h-3.5 w-3.5" />
            Analyze new BOM
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[1.05fr_1fr]">
          <div className="relative flex flex-col justify-between gap-4 border-b border-border bg-gradient-to-br from-primary/[0.06] via-surface to-surface p-4 lg:border-b-0 lg:border-r">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/[0.08] px-2 py-0.5 text-caption font-semibold uppercase tracking-wide text-primary">
                <Wand2 className="h-3 w-3" />
                Analyzer
              </span>
              <h2 className="mt-2.5 text-h2 font-semibold tracking-tight text-foreground">
                Analyze a new bill of materials
              </h2>
              <p className="mt-1 max-w-md text-small leading-relaxed text-muted-foreground">
                Parse a messy CSV, match each line to an emission factor, calculate the Scope 3
                Cat. 1 footprint, and surface hotspots — with every assumption reviewable.
              </p>
            </div>

            <ol className="space-y-1.5">
              {STEPS.map((step, i) => (
                <li key={step} className="flex items-center gap-2.5 text-small text-foreground">
                  <span className="num grid h-5 w-5 shrink-0 place-items-center rounded-full bg-primary/10 text-caption font-semibold text-primary">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>

            <div className="flex flex-wrap items-center gap-2 text-caption text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <ShieldCheck className="h-3 w-3 text-data-low" />
                GHG Protocol · PACT v3
              </span>
              <span className="text-border">·</span>
              <span>Open CEDA 2025</span>
            </div>
          </div>

          <div className="p-4">
            <Link
              href="/analyzer"
              className="group relative flex h-full min-h-[170px] flex-col items-center justify-center rounded-lg border border-dashed border-primary/35 bg-primary/[0.03] p-4 text-center transition-colors hover:bg-primary/[0.06]"
            >
              <span className="grid h-11 w-11 place-items-center rounded-lg bg-primary/10 text-primary ring-1 ring-primary/15">
                <UploadCloud className="h-5 w-5" />
              </span>
              <span className="mt-3 text-body font-semibold text-foreground">
                Open the analyzer to upload a BOM
              </span>
              <span className="mt-0.5 text-caption text-muted-foreground">
                single or bulk CSV import
              </span>

              <span className="mt-4 inline-flex items-center gap-2">
                <span className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1.5 text-small font-medium text-foreground shadow-xs">
                  <FileSpreadsheet className="h-3.5 w-3.5" />
                  Choose CSV
                </span>
                <span className="flex items-center gap-2 rounded-md bg-primary px-3 py-1.5 text-small font-semibold text-primary-foreground shadow-xs">
                  <Plus className="h-3.5 w-3.5" />
                  Open analyzer
                  <ArrowRight className="h-3 w-3 opacity-70 transition-transform group-hover:translate-x-0.5" />
                </span>
              </span>

              <span className="mt-4 flex flex-wrap items-center justify-center gap-1.5 text-caption text-muted-foreground">
                <span className="mr-1">Expected columns:</span>
                {EXPECTED_COLUMNS.map((col) => (
                  <span
                    key={col}
                    className="num rounded border border-border bg-surface-2 px-1.5 py-0.5 text-foreground"
                  >
                    {col}
                  </span>
                ))}
              </span>

              <span className="absolute right-3 top-3 inline-flex items-center gap-1 text-caption font-medium text-muted-foreground">
                <Sparkles className="h-3 w-3" />
                Sample BOM in analyzer
              </span>
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setOpen(false)}
            className="absolute right-3 top-3 grid h-6 w-6 place-items-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Collapse"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </section>
  );
}
