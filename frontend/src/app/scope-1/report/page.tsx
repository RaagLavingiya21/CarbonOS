"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Download, Lock } from "lucide-react";

import { MetricCard } from "@/components/data/MetricCard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { scope1Api, type S1Report, type S1Trace } from "@/lib/scope1-api";

import { ArToggle, InventoryPicker, fmtT, useInventories } from "../_lib";

function download(content: string, filename: string) {
  const blob = new Blob([content], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function Scope1ReportPage() {
  const { inventories, active, activeId, setActiveId, reload } = useInventories();
  const [arVersion, setArVersion] = useState("AR5");
  const [report, setReport] = useState<S1Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [traceId, setTraceId] = useState("");
  const [trace, setTrace] = useState<S1Trace | null>(null);

  const load = useCallback(async () => {
    if (!activeId) {
      setReport(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setReport(await scope1Api.report(activeId, arVersion));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [activeId, arVersion]);

  useEffect(() => {
    void load();
  }, [load]);

  async function lockInventory() {
    if (!activeId) return;
    try {
      await scope1Api.lockInventory(activeId);
      await reload();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function lookupTrace() {
    if (!traceId.trim()) return;
    try {
      setTrace(await scope1Api.recordTrace(traceId.trim(), arVersion));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/scope-1">
          <ArrowLeft className="h-4 w-4" />
          Back to Scope 1
        </Link>
      </Button>

      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-h1">Report</h1>
          <p className="mt-2 text-small text-muted-foreground">
            GHG Protocol / CA SB 253 inventory from one dataset. Biogenic CO₂ is a separate memo line.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <InventoryPicker inventories={inventories} activeId={activeId} onChange={setActiveId} />
          <ArToggle value={arVersion} onChange={setArVersion} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={!report}
          onClick={() => report && download(JSON.stringify(report, null, 2), `scope1-${active?.reporting_year}-${arVersion}.json`)}
        >
          <Download className="h-4 w-4" />
          Export (SB 253 / GHG Protocol)
        </Button>
        <Button type="button" variant="outline" disabled={!active || active.locked} onClick={lockInventory}>
          <Lock className="h-4 w-4" />
          {active?.locked ? "Locked" : "Lock period"}
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <Skeleton className="h-40 rounded-lg" />
      ) : report ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <MetricCard label={`Gross Scope 1 (${arVersion})`} value={fmtT(report.total_scope1_tco2e)} unit="tCO₂e" />
            <MetricCard
              label="Biogenic CO₂ (memo)"
              value={fmtT(report.biogenic_co2_tco2e)}
              unit="tCO₂e"
              hint="Excluded from the Scope 1 total"
            />
            <MetricCard label="Records" value={report.record_count} />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>By gas</CardTitle>
            </CardHeader>
            <CardContent>
              <table className="w-full text-left text-sm">
                <tbody>
                  {[
                    ["CO₂ (fossil)", report.by_gas.co2_fossil_tco2e],
                    ["CH₄", report.by_gas.ch4_tco2e],
                    ["N₂O", report.by_gas.n2o_tco2e],
                    ["SF₆", report.by_gas.sf6_tco2e],
                    ["NF₃", report.by_gas.nf3_tco2e],
                  ].map(([label, val]) => (
                    <tr key={label as string} className="border-t">
                      <td className="py-1.5">{label}</td>
                      <td className="py-1.5 text-right tabular-nums">{fmtT(val as number)} tCO₂e</td>
                    </tr>
                  ))}
                  <tr className="border-t font-semibold">
                    <td className="py-1.5">Total</td>
                    <td className="py-1.5 text-right tabular-nums">{fmtT(report.by_gas.total_tco2e)} tCO₂e</td>
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>

          {report.by_facility.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>By facility</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-left text-sm">
                  <tbody>
                    {report.by_facility.map((facility) => (
                      <tr key={facility.facility_id ?? "unassigned"} className="border-t">
                        <td className="py-1.5">{facility.facility_name ?? "Unassigned"}</td>
                        <td className="py-1.5 text-right tabular-nums">{fmtT(facility.tco2e)} tCO₂e</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : (
        <Alert>
          <AlertDescription>Select an inventory to view its report.</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>View source</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-64 flex-1 space-y-1.5">
              <Input
                placeholder="Paste a record id to trace its number"
                value={traceId}
                onChange={(event) => setTraceId(event.target.value)}
              />
            </div>
            <Button type="button" variant="outline" onClick={lookupTrace} disabled={!traceId.trim()}>
              Trace
            </Button>
          </div>
          {trace ? (
            <table className="w-full text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th className="py-1">Gas</th>
                  <th className="py-1 text-right">kg</th>
                  <th className="py-1 text-right">GWP-100</th>
                  <th className="py-1 text-right">tCO₂e</th>
                </tr>
              </thead>
              <tbody>
                {trace.gases.map((gas) => (
                  <tr key={gas.gas} className="border-t">
                    <td className="py-1">{gas.gas}</td>
                    <td className="py-1 text-right tabular-nums">{fmtT(gas.kg)}</td>
                    <td className="py-1 text-right tabular-nums">{gas.gwp_100}</td>
                    <td className="py-1 text-right tabular-nums">{fmtT(gas.tco2e)}</td>
                  </tr>
                ))}
                <tr className="border-t font-medium">
                  <td className="py-1">Total × multiplier {trace.consolidation_multiplier}</td>
                  <td />
                  <td />
                  <td className="py-1 text-right tabular-nums">{fmtT(trace.total_tco2e)}</td>
                </tr>
              </tbody>
              {trace.ef_source ? (
                <tfoot>
                  <tr>
                    <td colSpan={4} className="pt-2 text-caption text-muted-foreground">
                      {trace.ef_source} · tier {trace.ef_tier}
                    </td>
                  </tr>
                </tfoot>
              ) : null}
            </table>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
