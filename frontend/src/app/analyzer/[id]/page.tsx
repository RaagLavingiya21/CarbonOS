"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Copy, Download, FileWarning, RefreshCw } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
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
import { HotspotBar } from "@/components/data/HotspotBar";
import { MetricCard } from "@/components/data/MetricCard";
import { SourceCitation } from "@/components/data/SourceCitation";
import { Term } from "@/components/data/Term";
import { AnalysisDetail, api } from "@/lib/api";
import { getAnalysisFromSupabase } from "@/lib/supabase-data";
import { formatKg, formatPct } from "@/lib/utils";

function statusBadgeVariant(status: string | null | undefined) {
  if (status === "flagged") return "destructive" as const;
  if (status === "published") return "default" as const;
  return "secondary" as const;
}

export default function AnalysisDetailPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [pactPayload, setPactPayload] = useState<Record<string, unknown> | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAnalysisFromSupabase(params.id)
      .then(setAnalysis)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

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
                    <HotspotBar
                      label={item.component ?? "Unnamed component"}
                      sublabel={item.material ?? undefined}
                      sharePct={item.share_pct ?? 0}
                      value={`${formatKg(item.kg_co2e)} kg`}
                      emphasized={index === 0}
                    />
                    <div className="flex items-center justify-between gap-2 pl-0.5">
                      <span className="truncate text-caption text-muted-foreground">
                        {item.matched_sector ?? "unmatched"}
                      </span>
                      {item.ef_source ? <SourceCitation source={item.ef_source} /> : null}
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
