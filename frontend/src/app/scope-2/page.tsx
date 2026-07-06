"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Building2, Calculator, FileText, Mail, Upload, Zap } from "lucide-react";

import { KpiStrip } from "@/components/portfolio/KpiStrip";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Calculation, Coverage, Site, scope2Api } from "@/lib/scope2-api";
import { formatKg } from "@/lib/utils";

const ENTRIES = [
  {
    href: "/scope-2/sites",
    icon: Building2,
    title: "Sites & utility data",
    body: "Add your multi-site footprint from sector templates and import utility bills (CSV).",
  },
  {
    href: "/scope-2/calculate",
    icon: Calculator,
    title: "Calculate & report",
    body: "Run a dual-method (location + market-based) Scope 2 inventory with a full audit trail.",
  },
  {
    href: "/scope-2/landlord",
    icon: Mail,
    title: "Leased-site data requests",
    body: "Request whole-building or sub-metered data from landlords for leased sites — the gap no incumbent fills.",
  },
  {
    href: "/scope-2/reports",
    icon: FileText,
    title: "Buyer & CDP response",
    body: "Prefill CDP Supply Chain and buyer templates (Amazon) from one calculation — one number, many formats.",
  },
];

export default function Scope2Page() {
  const [sites, setSites] = useState<Site[] | null>(null);
  const [calcs, setCalcs] = useState<Calculation[] | null>(null);
  const [coverage, setCoverage] = useState<Coverage | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      scope2Api.listSites(),
      scope2Api.listCalculations(),
      scope2Api.coverage(),
    ])
      .then(([s, c, cov]) => {
        setSites(s);
        setCalcs(c);
        setCoverage(cov);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."));
  }, []);

  const latest = calcs?.[0];
  const loading = !error && (sites === null || calcs === null);

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <header className="mb-8 flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary">
          <Zap className="h-5 w-5" aria-hidden />
        </span>
        <div>
          <h1 className="text-h1 font-semibold">Scope 2 — Grid</h1>
          <p className="text-small text-muted-foreground">
            The Scope 2 system of record for multi-site consumer brands.
          </p>
        </div>
      </header>

      {error ? (
        <ErrorState
          title="Couldn't reach the Scope 2 service"
          message={error}
        />
      ) : loading ? (
        <Skeleton className="h-[92px] w-full rounded-lg" />
      ) : (
        <KpiStrip
          tiles={[
            { label: "Sites", value: sites?.length ?? 0 },
            {
              label: "Location-based",
              value: latest ? formatKg(latest.location_based_kg_co2e) : "—",
              unit: latest ? "kg CO₂e" : undefined,
              hint: latest ? `Reporting year ${latest.reporting_year}` : "No calculation yet",
            },
            {
              label: "Market-based",
              value: latest ? formatKg(latest.market_based_kg_co2e) : "—",
              unit: latest ? "kg CO₂e" : undefined,
              hint: latest ? `Reporting year ${latest.reporting_year}` : "No calculation yet",
            },
            {
              label: "Data coverage",
              value: coverage ? `${Math.round(coverage.coverage_fraction * 100)}%` : "—",
              bar: coverage ? coverage.coverage_fraction : 0,
              barTone:
                coverage && coverage.coverage_fraction >= 0.9 ? "success" : "warning",
              hint: coverage
                ? `${coverage.sites_missing_data} site(s) missing data`
                : "actual vs. estimate",
            },
          ]}
        />
      )}

      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        {ENTRIES.map((entry) => {
          const Icon = entry.icon;
          return (
            <Link key={entry.href} href={entry.href} className="group">
              <Card className="h-full transition-colors duration-micro ease-out hover:border-border-strong">
                <CardHeader>
                  <div className="mb-1 flex h-8 w-8 items-center justify-center rounded-md bg-accent text-accent-foreground">
                    <Icon className="h-4 w-4" />
                  </div>
                  <CardTitle className="flex items-center gap-1 text-h3">
                    {entry.title}
                    <ArrowRight className="h-3.5 w-3.5 -translate-x-1 opacity-0 transition-all duration-micro group-hover:translate-x-0 group-hover:opacity-100" />
                  </CardTitle>
                  <CardDescription>{entry.body}</CardDescription>
                </CardHeader>
              </Card>
            </Link>
          );
        })}
      </div>

      <p className="mt-6 flex items-center gap-1.5 text-caption text-muted-foreground">
        <Upload className="h-3 w-3" />
        Location-based and market-based totals are always reported separately, never merged
        (GHG Protocol Scope 2).
      </p>
    </div>
  );
}
