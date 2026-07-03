"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { AnalysisSummary, api } from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

function statusBadgeVariant(status: string | null | undefined) {
  if (status === "flagged") return "destructive" as const;
  if (status === "published") return "default" as const;
  return "secondary" as const;
}

function healthBadgeVariant(health: string | null | undefined) {
  if (health === "stale") return "destructive" as const;
  if (health === "attention") return "secondary" as const;
  return "outline" as const;
}

function ProductsPageContent() {
  const searchParams = useSearchParams();
  const statusFilter = searchParams.get("status");
  const healthFilter = searchParams.get("health");
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAnalyses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listAnalyses({
        status: statusFilter ?? undefined,
        health: healthFilter ?? undefined,
      });
      setAnalyses(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, healthFilter]);

  useEffect(() => {
    void loadAnalyses();
  }, [loadAnalyses]);

  const filterLabel = healthFilter
    ? `Health: ${healthFilter}`
    : statusFilter
      ? statusFilter.charAt(0).toUpperCase() + statusFilter.slice(1)
      : "All products";

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>
      </Button>

      <section>
        <h1 className="text-h1">Product portfolio</h1>
        <p className="mt-2 text-small text-muted-foreground">
          {filterLabel} — saved footprint analyses with lifecycle status and version.
        </p>
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Footprints</CardTitle>
          <CardDescription>
            Click a row to drill into line items, hotspots, and source citations.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((item) => (
                <Skeleton key={item} className="h-14 rounded-lg" />
              ))}
            </div>
          ) : error ? (
            <ErrorState
              title="Couldn't load portfolio"
              message={error}
              onRetry={() => void loadAnalyses()}
            />
          ) : analyses.length === 0 ? (
            <p className="py-8 text-center text-small text-muted-foreground">
              No saved products{statusFilter ? ` with status "${statusFilter}"` : ""} yet.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-secondary text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3">Product</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Health</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Total kg CO₂e</th>
                    <th className="px-4 py-3">Primary data share</th>
                    <th className="px-4 py-3">Flagged items</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {analyses.map((analysis) => (
                    <tr key={analysis.product_id} className="border-t bg-card">
                      <td className="px-4 py-3 font-medium">{analysis.product_name}</td>
                      <td className="px-4 py-3">
                        <Badge variant={statusBadgeVariant(analysis.status)}>
                          {analysis.status ?? "saved"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={healthBadgeVariant(analysis.health_status)}>
                          {analysis.health_status ?? "healthy"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 tabular-nums">{analysis.version ?? 1}</td>
                      <td className="px-4 py-3 tabular-nums">{formatKg(analysis.total_kg_co2e)}</td>
                      <td className="px-4 py-3 tabular-nums">
                        {formatPct((analysis.primary_data_share ?? 0) * 100)}
                      </td>
                      <td className="px-4 py-3 tabular-nums">{analysis.flagged_items}</td>
                      <td className="px-4 py-3 text-right">
                        <Button asChild size="sm" variant="ghost">
                          <Link href={`/analyzer/${analysis.product_id}`}>
                            View
                            <ArrowRight className="h-4 w-4" />
                          </Link>
                        </Button>
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

export default function ProductsPage() {
  return (
    <Suspense
      fallback={
        <div className="space-y-3">
          {[1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-14 rounded-lg" />
          ))}
        </div>
      }
    >
      <ProductsPageContent />
    </Suspense>
  );
}
