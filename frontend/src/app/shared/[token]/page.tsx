"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Download, Leaf } from "lucide-react";

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
import { HotspotBar } from "@/components/data/HotspotBar";
import { MetricCard } from "@/components/data/MetricCard";
import { SourceCitation } from "@/components/data/SourceCitation";
import { Term } from "@/components/data/Term";
import { Skeleton } from "@/components/ui/skeleton";
import { AnalysisLineItem, PublicSharedFootprint, api } from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

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

export default function SharedFootprintPage({ params }: { params: { token: string } }) {
  const [footprint, setFootprint] = useState<PublicSharedFootprint | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloadingPact, setDownloadingPact] = useState(false);

  useEffect(() => {
    api
      .fetchPublicFootprint(params.token)
      .then(setFootprint)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.token]);

  async function downloadPactJson() {
    setDownloadingPact(true);
    setError(null);
    try {
      const payload = await api.fetchPublicPact(params.token);
      const blob = new Blob([JSON.stringify(payload, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `shared-footprint-pact.json`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDownloadingPact(false);
    }
  }

  const aggregateDqr = footprint?.aggregate_dqr ?? {};
  const technologicalDqr = aggregateDqr.technological as number | null | undefined;
  const geographicalDqr = aggregateDqr.geographical as number | null | undefined;
  const temporalDqr = aggregateDqr.temporal as number | null | undefined;

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Leaf className="h-4 w-4" aria-hidden />
            </span>
            <span className="text-body font-display font-semibold">Carbon Analyzer</span>
            <Badge variant="neutral">Shared footprint</Badge>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link href="/">Home</Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 px-4 py-8">
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
            title="Shared footprint unavailable"
            message={error}
            onRetry={() => window.location.reload()}
          />
        ) : footprint ? (
          <>
            <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <Badge variant="default">Published</Badge>
                <h1 className="mt-3 text-h1">{footprint.product_name}</h1>
                <p className="mt-2 text-small text-muted-foreground">
                  Read-only product carbon footprint shared via secure link.
                </p>
              </div>
              <Button
                disabled={downloadingPact}
                onClick={() => void downloadPactJson()}
                type="button"
                variant="outline"
              >
                <Download className="h-4 w-4" />
                {downloadingPact ? "Preparing..." : "Download PACT JSON"}
              </Button>
            </section>

            <section className="grid gap-4 md:grid-cols-4">
              <MetricCard
                label="Total footprint"
                value={formatKg(footprint.total_kg_co2e)}
                unit="kg CO₂e"
                hint={
                  <>
                    <Term name="scope 3 category 1">Scope 3 Category 1</Term>,{" "}
                    <Term name="cradle-to-gate">cradle-to-gate</Term>
                  </>
                }
              />
              <MetricCard
                label="Matched line items"
                value={footprint.matched_items}
                hint="Included in total"
              />
              <MetricCard
                label="Flagged line items"
                value={footprint.flagged_items}
                hint="Need human review"
              />
              <MetricCard
                label="Primary data share"
                value={formatPct((footprint.primary_data_share ?? 0) * 100)}
                hint="Share of footprint from supplier-specific data"
              />
            </section>

            {technologicalDqr != null ? (
              <Card>
                <CardHeader>
                  <CardTitle>Data quality</CardTitle>
                  <CardDescription>
                    PACT Data Quality Rating (1 = best, 5 = worst): technological, geographical,
                    temporal.
                  </CardDescription>
                </CardHeader>
                <CardContent className="grid gap-4 md:grid-cols-3">
                  <MetricCard label="Technological DQR" value={technologicalDqr} />
                  <MetricCard
                    label="Geographical DQR"
                    value={geographicalDqr ?? "—"}
                  />
                  <MetricCard label="Temporal DQR" value={temporalDqr ?? "—"} />
                </CardContent>
              </Card>
            ) : null}

            <Card>
              <CardHeader>
                <CardTitle>Provenance / methodology</CardTitle>
                <CardDescription>
                  Method statement, per-line citations, and version lineage.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-small text-muted-foreground">
                  {footprint.method_statement.summary}
                </p>
                <p className="text-small text-muted-foreground">
                  {footprint.method_statement.detail}
                </p>
                <p className="text-small">
                  {footprint.version_lineage.length} version(s) in lineage · PDS{" "}
                  {formatPct((footprint.primary_data_share ?? 0) * 100)}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Emission hotspots</CardTitle>
                <CardDescription>
                  Line-item contribution to the total footprint, largest first.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[...footprint.line_items]
                  .filter((item) => item.kg_co2e != null)
                  .sort((a, b) => (b.share_pct ?? 0) - (a.share_pct ?? 0))
                  .map((item, index) => (
                    <div
                      key={`${item.component}-${item.material}-${index}`}
                      className="space-y-1.5"
                    >
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
                        <div className="flex items-center gap-2">
                          {formatLineDqr(item) ? (
                            <Badge variant="outline">{formatLineDqr(item)}</Badge>
                          ) : null}
                          {item.ef_source ? <SourceCitation source={item.ef_source} /> : null}
                        </div>
                      </div>
                    </div>
                  ))}
                {footprint.line_items.every((item) => item.kg_co2e == null) ? (
                  <p className="py-6 text-center text-small text-muted-foreground">
                    No matched line items to chart yet.
                  </p>
                ) : null}
              </CardContent>
            </Card>
          </>
        ) : null}
      </main>
    </div>
  );
}
