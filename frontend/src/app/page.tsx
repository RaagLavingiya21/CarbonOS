"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertCircle, ArrowRight, BarChart3, CheckCircle2, FileWarning } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import { AnalysisSummary } from "@/lib/api";
import { listAnalysesFromSupabase } from "@/lib/supabase-data";
import { formatKg } from "@/lib/utils";

export default function Home() {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAnalysesFromSupabase()
      .then(setAnalyses)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const totals = useMemo(() => {
    const totalKg = analyses.reduce((sum, item) => sum + item.total_kg_co2e, 0);
    const flagged = analyses.reduce((sum, item) => sum + item.flagged_items, 0);
    const matched = analyses.reduce((sum, item) => sum + item.matched_items, 0);
    return {
      totalKg,
      flagged,
      matched,
      completeness: matched + flagged === 0 ? 0 : Math.round((matched / (matched + flagged)) * 100),
    };
  }, [analyses]);

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <Badge variant="secondary">Production dashboard</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
            Product carbon footprint workspace
          </h1>
          <p className="mt-3 max-w-2xl text-muted-foreground">
            Review saved product analyses, identify Scope 3 hotspots, and move high-impact suppliers into engagement workflows.
          </p>
        </div>
        <Button asChild size="lg">
          <Link href="/analyzer">
            Upload BOM
            <ArrowRight className="h-4 w-4" />
          </Link>
        </Button>
      </section>

      {error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Could not load dashboard</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <section className="grid gap-4 md:grid-cols-3">
        <Card className="glass-card">
          <CardHeader>
            <CardDescription>Total analyzed footprint</CardDescription>
            <CardTitle className="text-3xl">{loading ? "..." : formatKg(totals.totalKg)}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="glass-card">
          <CardHeader>
            <CardDescription>Saved analyses</CardDescription>
            <CardTitle className="text-3xl">{loading ? "..." : analyses.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card className="glass-card">
          <CardHeader>
            <CardDescription>Matched data completeness</CardDescription>
            <CardTitle className="text-3xl">{loading ? "..." : `${totals.completeness}%`}</CardTitle>
          </CardHeader>
          <CardContent>
            <Progress value={totals.completeness} />
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Recent analyses</CardTitle>
          <CardDescription>Saved product footprints from the FastAPI backend.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((item) => (
                <div key={item} className="h-16 animate-pulse rounded-xl bg-secondary" />
              ))}
            </div>
          ) : analyses.length === 0 ? (
            <div className="rounded-xl border border-dashed p-8 text-center">
              <BarChart3 className="mx-auto h-8 w-8 text-muted-foreground" />
              <h3 className="mt-3 font-medium">No saved analyses yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">Upload a BOM to create your first auditable footprint.</p>
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border">
              {analyses.map((analysis) => (
                <Link
                  key={analysis.product_id}
                  href={`/analyzer/${analysis.product_id}`}
                  className="grid gap-3 border-b bg-white p-4 transition hover:bg-accent/50 md:grid-cols-[1fr_180px_140px_120px] md:items-center last:border-b-0"
                >
                  <div>
                    <p className="font-medium">{analysis.product_name}</p>
                    <p className="text-sm text-muted-foreground">{analysis.analysis_date}</p>
                  </div>
                  <div className="font-medium">{formatKg(analysis.total_kg_co2e)}</div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <CheckCircle2 className="h-4 w-4 text-primary" />
                    {analysis.matched_items} matched
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <FileWarning className="h-4 w-4 text-amber-500" />
                    {analysis.flagged_items} flagged
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
