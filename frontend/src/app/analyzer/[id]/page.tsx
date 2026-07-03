"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Copy, Download, FileWarning, FlaskConical, RefreshCw } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { HotspotBar } from "@/components/data/HotspotBar";
import { MetricCard } from "@/components/data/MetricCard";
import { SourceCitation } from "@/components/data/SourceCitation";
import { Term } from "@/components/data/Term";
import { AnalysisDetail, AnalysisLineItem, ApplyPrimaryDataResponse, FootprintProvenance, ScenarioSummary, api } from "@/lib/api";
import { getAnalysisFromSupabase } from "@/lib/supabase-data";
import { formatKg, formatPct } from "@/lib/utils";

function statusBadgeVariant(status: string | null | undefined) {
  if (status === "flagged") return "destructive" as const;
  if (status === "published") return "default" as const;
  return "secondary" as const;
}

function dataSourceBadgeVariant(dataSource: string | null | undefined) {
  if (dataSource === "primary") return "default" as const;
  return "outline" as const;
}

function formatLineDqr(item: AnalysisLineItem) {
  if (
    item.technological_dqr == null &&
    item.geographical_dqr == null &&
    item.temporal_dqr == null
  ) {
    return null;
  }
  return `T${item.technological_dqr ?? "—"}/G${item.geographical_dqr ?? "—"}/Y${item.temporal_dqr ?? "—"}`;
}

export default function AnalysisDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [pactPayload, setPactPayload] = useState<Record<string, unknown> | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [primaryDataOpen, setPrimaryDataOpen] = useState(false);
  const [selectedLineItem, setSelectedLineItem] = useState<AnalysisLineItem | null>(null);
  const [primaryKgCo2e, setPrimaryKgCo2e] = useState("");
  const [sourceNote, setSourceNote] = useState("");
  const [applyingPrimary, setApplyingPrimary] = useState(false);
  const [applyResult, setApplyResult] = useState<ApplyPrimaryDataResponse | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioSummary[]>([]);
  const [creatingScenario, setCreatingScenario] = useState(false);
  const [provenance, setProvenance] = useState<FootprintProvenance | null>(null);
  const [provenanceLoading, setProvenanceLoading] = useState(false);

  useEffect(() => {
    getAnalysisFromSupabase(params.id)
      .then(setAnalysis)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  useEffect(() => {
    if (!analysis?.product_id) return;
    api
      .listScenarios(analysis.product_id)
      .then(setScenarios)
      .catch(() => setScenarios([]));
  }, [analysis?.product_id]);

  useEffect(() => {
    if (!analysis?.product_id) return;
    setProvenanceLoading(true);
    api
      .fetchProvenance(analysis.product_id)
      .then((data) => setProvenance(data as FootprintProvenance))
      .catch(() => setProvenance(null))
      .finally(() => setProvenanceLoading(false));
  }, [analysis?.product_id]);

  async function downloadProvenance(format: "json" | "markdown") {
    if (!analysis) return;
    setError(null);
    try {
      const data = await api.fetchProvenance(analysis.product_id, format);
      const blob = new Blob(
        [typeof data === "string" ? data : JSON.stringify(data, null, 2)],
        { type: format === "markdown" ? "text/markdown" : "application/json" },
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `footprint-${analysis.product_id}-provenance.${format === "markdown" ? "md" : "json"}`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function exportCsv() {
    if (!analysis) return;
    setExporting(true);
    setError(null);
    try {
      const blob = await api.exportAnalysisCsv(params.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${analysis.product_name.replaceAll(" ", "_")}_footprint.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExporting(false);
    }
  }

  async function publishFootprint() {
    if (!analysis) return;
    setPublishing(true);
    setError(null);
    try {
      const response = await api.publishAnalysis(analysis.product_id);
      setAnalysis({
        ...analysis,
        status: response.status,
        published_at: response.published_at,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPublishing(false);
    }
  }

  async function createScenario() {
    if (!analysis) return;
    const defaultName = `Scenario: ${analysis.product_name}`;
    const name = window.prompt("Scenario name", defaultName);
    if (!name?.trim()) return;
    setCreatingScenario(true);
    setError(null);
    try {
      const result = await api.createScenario(analysis.product_id, { name: name.trim() });
      router.push(`/scenarios/${result.scenario_id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCreatingScenario(false);
    }
  }

  async function exportPactPayload() {
    if (!analysis) return;
    setExportLoading(true);
    setError(null);
    try {
      const payload = await api.fetchPactPayload(analysis.product_id);
      setPactPayload(payload);
      setExportOpen(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExportLoading(false);
    }
  }

  const pactJson = pactPayload ? JSON.stringify(pactPayload, null, 2) : "";

  async function copyPactJson() {
    if (!pactJson) return;
    await navigator.clipboard.writeText(pactJson);
  }

  function downloadPactJson() {
    if (!pactJson || !analysis) return;
    const blob = new Blob([pactJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `footprint-${analysis.product_id}-pact.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function openPrimaryDataSheet(item: AnalysisLineItem) {
    setSelectedLineItem(item);
    setPrimaryKgCo2e("");
    setSourceNote("");
    setApplyResult(null);
    setPrimaryDataOpen(true);
  }

  async function submitPrimaryData() {
    if (!analysis || !selectedLineItem?.item_id) return;
    const value = Number(primaryKgCo2e);
    if (!Number.isFinite(value) || value <= 0 || !sourceNote.trim()) return;
    setApplyingPrimary(true);
    setError(null);
    try {
      const result = await api.applyPrimaryData(analysis.product_id, {
        item_id: selectedLineItem.item_id,
        primary_kg_co2e: value,
        source_note: sourceNote.trim(),
      });
      setApplyResult(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setApplyingPrimary(false);
    }
  }

  const recalculateHref = analysis
    ? `/analyzer?recalculate_of=${analysis.product_id}&product_name=${encodeURIComponent(analysis.product_name)}`
    : "/analyzer";

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
      </Button>

      {loading ? (
        <div className="space-y-6">
          <Skeleton className="h-9 w-64" />
          <div className="grid gap-4 md:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <Skeleton key={item} className="h-24 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-lg" />
        </div>
      ) : error ? (
        <ErrorState
          title="Couldn't load this analysis"
          message={error}
          onRetry={() => window.location.reload()}
        />
      ) : analysis ? (
        <>
          <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={statusBadgeVariant(analysis.status)}>
                  {analysis.status ?? "saved"}
                </Badge>
                {analysis.version ? (
                  <Badge variant="outline">Version {analysis.version}</Badge>
                ) : null}
              </div>
              <h1 className="mt-3 text-h1">{analysis.product_name}</h1>
              <p className="mt-2 text-small text-muted-foreground">
                Analysis date: {analysis.analysis_date}
                {analysis.published_at
                  ? ` · Published ${new Date(analysis.published_at).toLocaleDateString()}`
                  : null}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {analysis.status === "approved" ? (
                <>
                  <Button
                    disabled={exportLoading}
                    onClick={exportPactPayload}
                    type="button"
                    variant="outline"
                  >
                    <Download className="h-4 w-4" />
                    {exportLoading ? "Loading..." : "Export PACT payload"}
                  </Button>
                  <Button disabled={publishing} onClick={publishFootprint} type="button">
                    {publishing ? "Publishing..." : "Publish"}
                  </Button>
                </>
              ) : analysis.status === "published" ? (
                <Button disabled type="button" variant="outline">
                  Published — read-only
                </Button>
              ) : null}
              <Button
                disabled={creatingScenario}
                onClick={createScenario}
                type="button"
                variant="outline"
              >
                <FlaskConical className="h-4 w-4" />
                {creatingScenario ? "Creating..." : "Model a scenario"}
              </Button>
              <Button asChild variant="ghost">
                <Link href={recalculateHref}>
                  <RefreshCw className="h-4 w-4" />
                  Recalculate
                </Link>
              </Button>
              <Button variant="outline" onClick={exportCsv} disabled={exporting}>
                <Download className="h-4 w-4" />
                {exporting ? "Exporting..." : "Export CSV"}
              </Button>
            </div>
          </section>

          {scenarios.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Scenarios</CardTitle>
                <CardDescription>
                  What-if models for this product. Scenarios are not published footprints.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {scenarios.map((scenario) => (
                  <div
                    key={scenario.scenario_id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"
                  >
                    <div>
                      <p className="font-medium">{scenario.name}</p>
                      <p className="text-small text-muted-foreground">
                        {formatKg(scenario.total_kg_co2e)}
                        {scenario.delta_pct != null ? (
                          <> · {formatPct(scenario.delta_pct)} vs baseline</>
                        ) : null}
                      </p>
                    </div>
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/scenarios/${scenario.scenario_id}`}>Compare</Link>
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          <Sheet open={exportOpen} onOpenChange={setExportOpen}>
            <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
              <SheetHeader>
                <SheetTitle>PACT v3 ProductFootprint</SheetTitle>
                <SheetDescription>
                  Preview and download the exported payload for product {analysis.product_id}.
                </SheetDescription>
              </SheetHeader>
              <div className="mt-4 space-y-3">
                <div className="flex gap-2">
                  <Button onClick={copyPactJson} size="sm" type="button" variant="outline">
                    <Copy className="h-4 w-4" />
                    Copy JSON
                  </Button>
                  <Button onClick={downloadPactJson} size="sm" type="button" variant="outline">
                    <Download className="h-4 w-4" />
                    Download .json
                  </Button>
                </div>
                <pre className="max-h-[70vh] overflow-auto rounded-xl border bg-secondary p-4 text-xs">
                  {pactJson}
                </pre>
              </div>
            </SheetContent>
          </Sheet>

          <Sheet open={primaryDataOpen} onOpenChange={setPrimaryDataOpen}>
            <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
              <SheetHeader>
                <SheetTitle>Enter supplier value</SheetTitle>
                <SheetDescription>
                  Apply primary cradle-to-gate data for{" "}
                  {selectedLineItem?.component ?? "this component"} /{" "}
                  {selectedLineItem?.material ?? "material"}. This creates a new footprint version.
                </SheetDescription>
              </SheetHeader>
              {applyResult ? (
                <Alert className="mt-4" variant="success">
                  <AlertTitle>Primary data applied</AlertTitle>
                  <AlertDescription className="space-y-2">
                    <p>
                      Created v{applyResult.version}, PDS{" "}
                      {formatPct(applyResult.pds_before * 100)} →{" "}
                      {formatPct(applyResult.pds_after * 100)}
                    </p>
                    <Button asChild size="sm" variant="outline">
                      <Link href={`/analyzer/${applyResult.new_product_id}`}>
                        View new version
                      </Link>
                    </Button>
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="mt-4 space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="primary-kg">Cradle-to-gate kg CO₂e</Label>
                    <Input
                      id="primary-kg"
                      inputMode="decimal"
                      min="0"
                      placeholder="e.g. 12.5"
                      type="number"
                      value={primaryKgCo2e}
                      onChange={(event) => setPrimaryKgCo2e(event.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="source-note">Source note</Label>
                    <Textarea
                      id="source-note"
                      placeholder="Supplier name, document reference, or method note"
                      value={sourceNote}
                      onChange={(event) => setSourceNote(event.target.value)}
                    />
                  </div>
                  <Button
                    disabled={
                      applyingPrimary ||
                      !primaryKgCo2e ||
                      Number(primaryKgCo2e) <= 0 ||
                      !sourceNote.trim()
                    }
                    onClick={submitPrimaryData}
                    type="button"
                  >
                    {applyingPrimary ? "Applying..." : "Confirm and create new version"}
                  </Button>
                </div>
              )}
            </SheetContent>
          </Sheet>

          {analysis.flagged_comment ? (
            <Alert>
              <FileWarning className="h-4 w-4" />
              <AlertDescription>{analysis.flagged_comment}</AlertDescription>
            </Alert>
          ) : null}

          <section className="grid gap-4 md:grid-cols-4">
            <MetricCard
              label="Total footprint"
              value={formatKg(analysis.total_kg_co2e)}
              unit="kg CO₂e"
              hint={
                <>
                  <Term name="scope 3 category 1">Scope 3 Category 1</Term>,{" "}
                  <Term name="cradle-to-gate">cradle-to-gate</Term>
                </>
              }
            />
            <MetricCard label="Matched line items" value={analysis.matched_items} hint="Included in total" />
            <MetricCard label="Flagged line items" value={analysis.flagged_items} hint="Need human review" />
            <MetricCard
              label="Primary data share"
              value={formatPct((analysis.primary_data_share ?? 0) * 100)}
              hint="Share of footprint from supplier-specific data"
            />
          </section>

          {analysis.technological_dqr != null ? (
            <Card>
              <CardHeader>
                <CardTitle>Data quality</CardTitle>
                <CardDescription>
                  PACT Data Quality Rating (1 = best, 5 = worst): technological, geographical,
                  temporal.
                </CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <MetricCard
                  label="Technological DQR"
                  value={analysis.technological_dqr}
                  hint="Primary data = 1; secondary by EF confidence"
                />
                <MetricCard
                  label="Geographical DQR"
                  value={analysis.geographical_dqr ?? "—"}
                  hint="Country-specific activity data vs global fallback"
                />
                <MetricCard
                  label="Temporal DQR"
                  value={analysis.temporal_dqr ?? "—"}
                  hint="Reporting period vs Open CEDA 2025 vintage"
                />
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>Provenance / methodology</CardTitle>
              <CardDescription>
                Auditor-facing traceability: method statement, per-line citations, and version
                lineage.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {provenanceLoading ? (
                <Skeleton className="h-20 w-full" />
              ) : provenance ? (
                <>
                  <p className="text-small text-muted-foreground">
                    {provenance.method_statement.summary}
                  </p>
                  <p className="text-small">
                    {provenance.version_lineage.length} version(s) in lineage · PDS{" "}
                    {formatPct((provenance.primary_data_share ?? 0) * 100)}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={() => void downloadProvenance("json")}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      <Download className="h-4 w-4" />
                      Download methodology (.json)
                    </Button>
                    <Button
                      onClick={() => void downloadProvenance("markdown")}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      <Download className="h-4 w-4" />
                      Download methodology (.md)
                    </Button>
                  </div>
                </>
              ) : (
                <p className="text-small text-muted-foreground">
                  Provenance unavailable for this footprint.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Emission hotspots</CardTitle>
              <CardDescription>
                Line-item contribution to the total footprint, largest first. Each{" "}
                <Term name="hotspot">hotspot</Term> shows the{" "}
                <Term name="emission factor">emission factor</Term> source it used.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[...analysis.line_items]
                .filter((item) => item.kg_co2e != null)
                .sort((a, b) => (b.share_pct ?? 0) - (a.share_pct ?? 0))
                .map((item, index) => (
                  <div key={`${item.component}-${item.material}-${index}`} className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <HotspotBar
                        label={item.component ?? "Unnamed component"}
                        sublabel={item.material ?? undefined}
                        sharePct={item.share_pct ?? 0}
                        value={`${formatKg(item.kg_co2e)} kg`}
                        emphasized={index === 0}
                      />
                      <Badge variant={dataSourceBadgeVariant(item.data_source)}>
                        {item.data_source === "primary" ? "Primary" : "Secondary"}
                      </Badge>
                      {item.data_source !== "primary" && item.item_id ? (
                        <Button
                          onClick={() => openPrimaryDataSheet(item)}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          Enter supplier value
                        </Button>
                      ) : null}
                    </div>
                    <div className="flex items-center justify-between gap-2 pl-0.5">
                      <span className="truncate text-caption text-muted-foreground">
                        {item.matched_sector ?? "unmatched"}
                      </span>
                      <div className="flex items-center gap-2">
                        {formatLineDqr(item) ? (
                          <Badge variant="outline">{formatLineDqr(item)}</Badge>
                        ) : null}
                        {item.ef_source ? <SourceCitation source={item.ef_source} /> : null}
                      </div>
                    </div>
                  </div>
                ))}
              {analysis.line_items.every((item) => item.kg_co2e == null) ? (
                <p className="py-6 text-center text-small text-muted-foreground">
                  No matched line items to chart yet.
                </p>
              ) : null}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
