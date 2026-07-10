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
import {
  scope1Api,
  type S1AssuranceStatus,
  type S1AuditEntry,
  type S1Report,
  type S1TierBreakdown,
  type S1Trace,
} from "@/lib/scope1-api";

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
  const [audit, setAudit] = useState<S1AuditEntry[]>([]);
  const [assurance, setAssurance] = useState<S1AssuranceStatus | null>(null);
  const [dataQuality, setDataQuality] = useState<S1TierBreakdown | null>(null);

  const load = useCallback(async () => {
    if (!activeId) {
      setReport(null);
      setDataQuality(null);
      setAssurance(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [rep, assur, dq] = await Promise.all([
        scope1Api.report(activeId, arVersion),
        scope1Api.getAssurance(activeId).catch(() => null),
        scope1Api.getDataQuality(activeId, arVersion).catch(() => null),
      ]);
      setReport(rep);
      setAssurance(assur);
      setDataQuality(dq);
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
      const [tr, au] = await Promise.all([
        scope1Api.recordTrace(traceId.trim(), arVersion),
        scope1Api.recordAudit(traceId.trim()),
      ]);
      setTrace(tr);
      setAudit(au);
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

      {activeId ? (
        <p className="text-small text-muted-foreground">
          Assurance:{" "}
          <span className="font-medium text-foreground">
            {assurance && assurance.assurance_level && assurance.assurance_level !== "none"
              ? `${assurance.assurance_level} assurance${
                  assurance.assurance_standard
                    ? ` (${assurance.assurance_standard.replace(/_/g, " ")})`
                    : ""
                }${assurance.statement_on_file ? " · statement on file" : ""}`
              : "Not yet third-party verified"}
          </span>{" "}
          — set it in{" "}
          <Link href="/scope-1/setup" className="underline-offset-4 hover:underline">
            Setup
          </Link>
          . Exports reflect this status.
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={!report || !activeId}
          onClick={() =>
            activeId &&
            scope1Api.downloadSb253Pdf(activeId, arVersion).catch((err) => setError((err as Error).message))
          }
        >
          <Download className="h-4 w-4" />
          SB 253 disclosure (PDF)
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={!report || !activeId}
          onClick={() =>
            activeId &&
            scope1Api.downloadXlsx(activeId, arVersion).catch((err) => setError((err as Error).message))
          }
        >
          <Download className="h-4 w-4" />
          Export XLSX
        </Button>
        {(
          [
            { slug: "esrs-e1", label: "ESRS E1" },
            { slug: "cdp", label: "CDP" },
            { slug: "epa-ghgrp", label: "EPA GHGRP" },
          ] as const
        ).flatMap((r) =>
          (["pdf", "xlsx"] as const).map((ext) => (
            <Button
              key={`${r.slug}-${ext}`}
              type="button"
              variant="outline"
              disabled={!report || !activeId}
              onClick={() =>
                activeId &&
                scope1Api
                  .downloadDisclosure(activeId, r.slug, ext, arVersion)
                  .catch((err) => setError((err as Error).message))
              }
            >
              <Download className="h-4 w-4" />
              {r.label} ({ext.toUpperCase()})
            </Button>
          )),
        )}
        <Button
          type="button"
          variant="outline"
          disabled={!report}
          onClick={() => report && download(JSON.stringify(report, null, 2), `scope1-${active?.reporting_year}-${arVersion}.json`)}
        >
          <Download className="h-4 w-4" />
          JSON
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

          {dataQuality && dataQuality.rows.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Data quality by tier</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-left text-sm">
                  <thead className="text-caption text-muted-foreground">
                    <tr>
                      <th className="py-1.5">Tier</th>
                      <th className="py-1.5 text-right">Records</th>
                      <th className="py-1.5 text-right">tCO₂e</th>
                      <th className="py-1.5 text-right">% of total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dataQuality.rows.map((row) => (
                      <tr key={row.tier} className="border-t">
                        <td className="py-1.5">
                          <span className="font-mono">T{row.tier}</span>{" "}
                          <span className="text-muted-foreground">{row.label}</span>
                        </td>
                        <td className="py-1.5 text-right tabular-nums">{row.count}</td>
                        <td className="py-1.5 text-right tabular-nums">{fmtT(row.tco2e)}</td>
                        <td className="py-1.5 text-right tabular-nums">{row.pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-caption text-muted-foreground">
                  Share of gross Scope 1 (combustion + fugitive + process) by input data quality
                  (T1 measured … T5 estimated). Included in the disclosure exports.
                </p>
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
                      {trace.evidence_document_id ? ` · evidence ${trace.evidence_document_id.slice(0, 8)}…` : " · no evidence attached"}
                    </td>
                  </tr>
                </tfoot>
              ) : null}
            </table>
          ) : null}
          {trace && audit.length > 0 ? (
            <div className="mt-3 border-t pt-3">
              <p className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
                Audit trail
              </p>
              <ul className="mt-1 space-y-0.5">
                {audit.map((entry, index) => (
                  <li key={index} className="text-caption text-muted-foreground">
                    {entry.action}
                    {entry.created_at ? ` · ${new Date(entry.created_at).toLocaleString()}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
