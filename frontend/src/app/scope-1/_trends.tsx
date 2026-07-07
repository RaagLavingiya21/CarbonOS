"use client";

import { useCallback, useEffect, useState } from "react";
import { TrendingDown, TrendingUp } from "lucide-react";

import { MetricCard } from "@/components/data/MetricCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { scope1Api, type S1Trends } from "@/lib/scope1-api";

import { fmtT } from "./_lib";

function fmtPct(v: number | null): string {
  if (v === null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

function fmtNum(v: number | null, digits = 2): string {
  if (v === null) return "—";
  return v.toLocaleString(undefined, { maximumFractionDigits: digits });
}

/**
 * Year-over-year Scope 1 totals + emissions intensity for the org, at the
 * selected AR version. Self-hides until there's at least one inventory total.
 */
export function TrendsPanel({ arVersion }: { arVersion: string }) {
  const [data, setData] = useState<S1Trends | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await scope1Api.trends(arVersion));
    } catch {
      setData(null);
    }
  }, [arVersion]);

  useEffect(() => {
    void load();
  }, [load]);

  if (!data || data.points.length === 0) return null;

  const max = Math.max(...data.points.map((p) => p.total_tco2e), 1);
  const latest = data.points[data.points.length - 1];
  const declining = (data.latest_vs_base_pct ?? 0) < 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trend &amp; intensity ({arVersion})</CardTitle>
        <CardDescription>
          Gross Scope 1 by reporting year
          {data.base_year != null && data.base_year_total_tco2e != null
            ? ` · vs base year ${data.base_year}`
            : ""}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-end gap-4 overflow-x-auto pb-2" style={{ minHeight: 160 }}>
          {data.points.map((p) => (
            <div key={p.inventory_id} className="flex min-w-14 flex-1 flex-col items-center gap-2">
              <span className="text-caption text-muted-foreground">{fmtT(p.total_tco2e)}</span>
              <div className="flex h-28 w-full items-end">
                <div
                  className={`w-full rounded-t ${p.is_base_year ? "bg-primary/40" : "bg-primary"}`}
                  style={{ height: `${Math.max(4, (p.total_tco2e / max) * 100)}%` }}
                  title={`${p.reporting_year}: ${p.total_tco2e} tCO₂e`}
                />
              </div>
              <span className="text-caption font-medium">{p.reporting_year}</span>
              <span
                className={`text-caption ${
                  p.yoy_pct == null
                    ? "text-muted-foreground"
                    : p.yoy_pct > 0
                      ? "text-data-high"
                      : "text-emerald-600"
                }`}
              >
                {p.yoy_pct == null ? (p.is_base_year ? "base" : "—") : fmtPct(p.yoy_pct)}
              </span>
            </div>
          ))}
        </div>

        {data.latest_vs_base_pct != null ? (
          <div className="flex items-center gap-2 rounded-md border bg-secondary/40 px-3 py-2 text-small">
            {declining ? (
              <TrendingDown className="h-4 w-4 text-emerald-600" />
            ) : (
              <TrendingUp className="h-4 w-4 text-data-high" />
            )}
            <span>
              {latest.reporting_year} is <span className="font-medium">{fmtPct(data.latest_vs_base_pct)}</span>{" "}
              vs base year {data.base_year} ({fmtT(Math.abs(data.latest_vs_base_abs ?? 0))} tCO₂e{" "}
              {declining ? "below" : "above"}).
            </span>
          </div>
        ) : null}

        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard
            label="Intensity / revenue"
            value={fmtNum(latest.per_revenue_mm)}
            unit={`tCO₂e / $M ${latest.revenue_currency}`}
            hint={latest.per_revenue_mm == null ? "Add annual revenue in Setup" : `${latest.reporting_year}`}
          />
          <MetricCard
            label="Intensity / output"
            value={fmtNum(latest.per_output, 4)}
            unit={latest.output_unit ? `tCO₂e / ${latest.output_unit}` : "tCO₂e / unit"}
            hint={latest.per_output == null ? "Add output in Setup" : `${latest.reporting_year}`}
          />
          <MetricCard
            label="Intensity / headcount"
            value={fmtNum(latest.per_headcount, 3)}
            unit="tCO₂e / FTE"
            hint={latest.per_headcount == null ? "Add headcount in Setup" : `${latest.reporting_year}`}
          />
        </div>
      </CardContent>
    </Card>
  );
}
