"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, BarChart3, Download, FileWarning } from "lucide-react";

import { MetricCard } from "@/components/data/MetricCard";
import { Term } from "@/components/data/Term";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { RollupSummary, api } from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

const YEAR_OPTIONS = Array.from({ length: 6 }, (_, index) => new Date().getFullYear() - index);

function downloadBlob(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function rollupToCsv(rollup: RollupSummary): string {
  const header = [
    "product_id",
    "product_name",
    "per_unit_kg_co2e",
    "annual_volume",
    "contribution_kg_co2e",
    "share_pct",
  ].join(",");
  const rows = rollup.breakdown.map((row) =>
    [
      row.product_id,
      `"${row.product_name.replaceAll('"', '""')}"`,
      row.per_unit_kg_co2e,
      row.annual_volume,
      row.contribution_kg_co2e,
      row.share_pct,
    ].join(","),
  );
  return [header, ...rows].join("\n");
}

export default function RollupPage() {
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);
  const [rollup, setRollup] = useState<RollupSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRollup = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.fetchRollup(year);
      setRollup(data);
    } catch (err) {
      setError((err as Error).message);
      setRollup(null);
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => {
    void loadRollup();
  }, [loadRollup]);

  const isIncomplete = useMemo(
    () => (rollup?.products_missing_volume.length ?? 0) > 0,
    [rollup],
  );

  function exportJson() {
    if (!rollup) return;
    downloadBlob(
      JSON.stringify(rollup, null, 2),
      `corporate-footprint-${rollup.year}.json`,
      "application/json",
    );
  }

  function exportCsv() {
    if (!rollup) return;
    downloadBlob(
      rollupToCsv(rollup),
      `corporate-footprint-${rollup.year}.csv`,
      "text/csv",
    );
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
      </Button>

      <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-muted-foreground" />
            <h1 className="text-h1">Corporate footprint</h1>
          </div>
          <p className="mt-2 text-small text-muted-foreground">
            Scope 3 Category 1 roll-up from published product footprints multiplied by annual
            volume.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-2">
            <Label htmlFor="rollup-year">Reporting year</Label>
            <Input
              id="rollup-year"
              type="number"
              list="rollup-year-options"
              value={year}
              onChange={(event) => setYear(Number(event.target.value))}
              className="w-28"
            />
            <datalist id="rollup-year-options">
              {YEAR_OPTIONS.map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
          </div>
          <Button
            type="button"
            variant="outline"
            disabled={!rollup}
            onClick={exportCsv}
          >
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!rollup}
            onClick={exportJson}
          >
            <Download className="h-4 w-4" />
            Export JSON
          </Button>
        </div>
      </section>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-28 rounded-lg" />
          <Skeleton className="h-64 rounded-lg" />
        </div>
      ) : error && !rollup ? (
        <ErrorState
          title="Couldn't load corporate footprint"
          message={error}
          onRetry={() => void loadRollup()}
        />
      ) : rollup ? (
        <>
          <MetricCard
            label="Scope 3 Category 1 total"
            value={formatKg(rollup.scope3_cat1_total_kg_co2e)}
            unit="kg CO₂e"
            hint={
              <>
                <Term name="scope 3 category 1">Purchased goods</Term> · {rollup.year} ·{" "}
                {rollup.product_count} product(s) with volume
              </>
            }
            footer={
              isIncomplete ? (
                <span className="text-caption text-amber-600 dark:text-amber-400">
                  Total is incomplete — some published products are missing volume for {rollup.year}.
                </span>
              ) : null
            }
          />

          {isIncomplete ? (
            <Alert>
              <FileWarning className="h-4 w-4" />
              <AlertTitle>Missing annual volume</AlertTitle>
              <AlertDescription>
                <p className="mb-2">
                  These published products match {rollup.year} but have no volume set. They are
                  excluded from the total above — not counted as zero.
                </p>
                <ul className="list-disc space-y-1 pl-5">
                  {rollup.products_missing_volume.map((product) => (
                    <li key={product.product_id}>
                      <Link
                        href={`/analyzer/${product.product_id}`}
                        className="font-medium underline-offset-4 hover:underline"
                      >
                        {product.product_name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Per-product breakdown</CardTitle>
              <CardDescription>
                Latest published version per product lineage for {rollup.year}.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {rollup.breakdown.length === 0 ? (
                <p className="text-small text-muted-foreground">
                  No published products with volume for {rollup.year}. Set annual volume on product
                  footprints to include them here.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-xl border">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="bg-secondary text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3">Product</th>
                        <th className="px-4 py-3 text-right">Per unit (kg CO₂e)</th>
                        <th className="px-4 py-3 text-right">Annual volume</th>
                        <th className="px-4 py-3 text-right">Contribution (kg CO₂e)</th>
                        <th className="px-4 py-3 text-right">Share</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rollup.breakdown.map((row) => (
                        <tr key={row.product_id} className="border-t bg-card">
                          <td className="px-4 py-3">
                            <Link
                              href={`/analyzer/${row.product_id}`}
                              className="font-medium underline-offset-4 hover:underline"
                            >
                              {row.product_name}
                            </Link>
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {formatKg(row.per_unit_kg_co2e)}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {row.annual_volume.toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {formatKg(row.contribution_kg_co2e)}
                          </td>
                          <td className="px-4 py-3 text-right tabular-nums">
                            {formatPct(row.share_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
