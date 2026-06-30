"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Download, FileWarning } from "lucide-react";

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
import { Skeleton } from "@/components/ui/skeleton";
import { HotspotBar } from "@/components/data/HotspotBar";
import { MetricCard } from "@/components/data/MetricCard";
import { SourceCitation } from "@/components/data/SourceCitation";
import { Term } from "@/components/data/Term";
import { AnalysisDetail, api } from "@/lib/api";
import { getAnalysisFromSupabase } from "@/lib/supabase-data";
import { formatKg } from "@/lib/utils";

export default function AnalysisDetailPage({ params }: { params: { id: string } }) {
  const [analysis, setAnalysis] = useState<AnalysisDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
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
              <Badge variant={analysis.status === "flagged" ? "destructive" : "secondary"}>
                {analysis.status ?? "saved"}
              </Badge>
              <h1 className="mt-3 text-h1">{analysis.product_name}</h1>
              <p className="mt-2 text-small text-muted-foreground">
                Analysis date: {analysis.analysis_date}
              </p>
            </div>
            <Button variant="outline" onClick={exportCsv} disabled={exporting}>
              <Download className="h-4 w-4" />
              {exporting ? "Exporting..." : "Export CSV"}
            </Button>
          </section>

          {analysis.flagged_comment ? (
            <Alert>
              <FileWarning className="h-4 w-4" />
              <AlertDescription>{analysis.flagged_comment}</AlertDescription>
            </Alert>
          ) : null}

          <section className="grid gap-4 md:grid-cols-3">
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
