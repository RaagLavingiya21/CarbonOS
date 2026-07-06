"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, Calculator, MapPin, ShoppingCart } from "lucide-react";

import { MetricCard } from "@/components/data/MetricCard";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Calculation, RunCalculationResult, scope2Api } from "@/lib/scope2-api";
import { formatKg } from "@/lib/utils";

const YEARS = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i);

export default function Scope2CalculatePage() {
  const [year, setYear] = useState(String(YEARS[1]));
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<RunCalculationResult | null>(null);
  const [calcs, setCalcs] = useState<Calculation[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    scope2Api
      .listCalculations()
      .then(setCalcs)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."));
  }, []);

  useEffect(() => load(), [load]);

  async function run() {
    setRunning(true);
    setError(null);
    try {
      setResult(await scope2Api.runCalculation(Number(year)));
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Calculation failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <Link
        href="/scope-2"
        className="mb-4 inline-flex items-center gap-1 text-small text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Scope 2
      </Link>
      <h1 className="text-h1 font-semibold">Calculate & report</h1>
      <p className="mb-6 text-small text-muted-foreground">
        Dual-method inventory across all active, non-franchise sites.
      </p>

      {error ? <ErrorState className="mb-6" title="Something went wrong" message={error} /> : null}

      <Card className="mb-6">
        <CardContent className="flex flex-wrap items-end gap-4 pt-6">
          <div className="space-y-1.5">
            <Label>Reporting year</Label>
            <Select value={year} onValueChange={setYear}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {YEARS.map((y) => (
                  <SelectItem key={y} value={String(y)}>
                    {y}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={run} loading={running}>
            <Calculator className="h-3.5 w-3.5" /> Run calculation
          </Button>
        </CardContent>
      </Card>

      {result ? (
        <section className="mb-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <MetricCard
              label="Location-based"
              value={formatKg(result.location_based_kg_co2e)}
              unit="kg CO₂e"
              hint={
                <span className="inline-flex items-center gap-1">
                  <MapPin className="h-3 w-3" /> Grid-average factors
                </span>
              }
            />
            <MetricCard
              label="Market-based"
              value={formatKg(result.market_based_kg_co2e)}
              unit="kg CO₂e"
              hint={
                <span className="inline-flex items-center gap-1">
                  <ShoppingCart className="h-3 w-3" /> Contractual instruments + residual mix
                </span>
              }
            />
          </div>
          <p className="mt-2 text-caption text-muted-foreground">
            {result.consumption_mwh.toFixed(1)} MWh across {result.site_count} site
            {result.site_count === 1 ? "" : "s"} · reporting year {result.reporting_year} ·
            calculation #{result.calc_id}
          </p>

          {result.market_fallback_site_count > 0 ? (
            <Alert className="mt-3 border-data-medium/40 bg-data-medium-bg/40">
              <AlertTriangle className="h-4 w-4 text-data-medium" />
              <AlertTitle>Market-based used a grid-average fallback</AlertTitle>
              <AlertDescription>
                {result.market_fallback_site_count} site
                {result.market_fallback_site_count === 1 ? "" : "s"} had no residual-mix factor, so
                grid-average was used for uncovered load. Add residual-mix factors to strengthen the
                market-based number.
              </AlertDescription>
            </Alert>
          ) : null}
        </section>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle className="text-h3">Prior calculations</CardTitle>
          <CardDescription>Each run is an immutable snapshot with an audit trail.</CardDescription>
        </CardHeader>
        <CardContent>
          {calcs === null ? (
            <Skeleton className="h-32 w-full" />
          ) : calcs.length === 0 ? (
            <EmptyState
              icon={Calculator}
              title="No calculations yet"
              description="Run your first dual-method inventory above."
            />
          ) : (
            <div className="overflow-hidden rounded-md border border-border">
              <table className="w-full text-small">
                <thead className="bg-surface-2 text-caption uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Year</th>
                    <th className="px-3 py-2 text-right font-medium">Location-based</th>
                    <th className="px-3 py-2 text-right font-medium">Market-based</th>
                    <th className="px-3 py-2 text-right font-medium">MWh</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {calcs.map((c) => (
                    <tr key={c.calc_id} className="num hover:bg-secondary/40">
                      <td className="px-3 py-2">{c.reporting_year}</td>
                      <td className="px-3 py-2 text-right">{formatKg(c.location_based_kg_co2e)}</td>
                      <td className="px-3 py-2 text-right">{formatKg(c.market_based_kg_co2e)}</td>
                      <td className="px-3 py-2 text-right text-muted-foreground">
                        {c.consumption_mwh?.toFixed(1) ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
