"use client";

import { Zap } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// Phase 0 shell for the Scope 2 ("Grid") module. Renders an empty, isolated
// dashboard scaffold. Site master, ingestion, leased-site workflow, dual-method
// calc, and reporting land in phases M0-M3.
const MODULES = [
  {
    title: "Sites & utility data",
    body: "Import your multi-site footprint, auto-classify from sector templates, and connect utilities (aggregator, CSV, or PDF).",
  },
  {
    title: "Leased-site workflow",
    body: "Request whole-building or sub-metered data from landlords, or fall back to documented, audit-labeled estimation.",
  },
  {
    title: "Dual-method calculation",
    body: "Location-based and market-based Scope 2 totals from one dataset, with a full audit trail.",
  },
  {
    title: "Buyer & CDP response",
    body: "Generate a CDP Supply Chain disclosure and retail-buyer responses without re-keying.",
  },
];

export default function Scope2Page() {
  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
          <Zap className="h-5 w-5" aria-hidden />
        </span>
        <div>
          <h1 className="text-heading font-semibold">Scope 2 — Grid</h1>
          <p className="text-small text-muted-foreground">
            The Scope 2 system of record for multi-site consumer brands. Module scaffold —
            features arrive across phases M0–M3.
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {MODULES.map((m) => (
          <Card key={m.title}>
            <CardHeader>
              <CardTitle className="text-body">{m.title}</CardTitle>
              <CardDescription>{m.body}</CardDescription>
            </CardHeader>
            <CardContent>
              <span className="text-small text-muted-foreground">Coming soon</span>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
