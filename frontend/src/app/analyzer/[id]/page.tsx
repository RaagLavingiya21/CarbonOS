"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Download, FileWarning } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { AnalysisDetail, api } from "@/lib/api";
import { getAnalysisFromSupabase } from "@/lib/supabase-data";
import { formatKg, formatPct } from "@/lib/utils";

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
        <Card>
          <CardContent className="p-8">
            <div className="h-8 w-64 animate-pulse rounded bg-secondary" />
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-28 animate-pulse rounded-xl bg-secondary" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : analysis ? (
        <>
          <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <Badge variant={analysis.status === "flagged" ? "destructive" : "secondary"}>
                {analysis.status ?? "saved"}
              </Badge>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight">{analysis.product_name}</h1>
              <p className="mt-2 text-muted-foreground">Analysis date: {analysis.analysis_date}</p>
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
            <Card className="">
              <CardHeader>
                <CardDescription>Total footprint</CardDescription>
                <CardTitle className="text-3xl">{formatKg(analysis.total_kg_co2e)}</CardTitle>
              </CardHeader>
            </Card>
            <Card className="">
              <CardHeader>
                <CardDescription>Matched line items</CardDescription>
                <CardTitle className="text-3xl">{analysis.matched_items}</CardTitle>
              </CardHeader>
            </Card>
            <Card className="">
              <CardHeader>
                <CardDescription>Flagged line items</CardDescription>
                <CardTitle className="text-3xl">{analysis.flagged_items}</CardTitle>
              </CardHeader>
            </Card>
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Emission breakdown</CardTitle>
              <CardDescription>Line-item contribution to total product footprint.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {analysis.line_items.map((item) => (
                <div key={`${item.component}-${item.material}`} className="rounded-xl border p-4">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="font-medium">{item.component ?? "Unnamed component"}</p>
                      <p className="text-sm text-muted-foreground">
                        {item.material ?? "Unknown material"} {"->"} {item.matched_sector ?? "No factor"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-semibold">{formatKg(item.kg_co2e)}</p>
                      <p className="text-sm text-muted-foreground">{formatPct(item.share_pct)}</p>
                    </div>
                  </div>
                  <Progress className="mt-3" value={Math.min(item.share_pct ?? 0, 100)} />
                  <p className="mt-2 text-xs text-muted-foreground">{item.ef_source ?? "No source cited"}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
