"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, Database, Flame, ListChecks, Settings2, FileText, Users } from "lucide-react";

import { MetricCard } from "@/components/data/MetricCard";
import { ModuleIntro } from "@/components/modules/ModuleIntro";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { scope1Api, type S1Readiness, type S1Report } from "@/lib/scope1-api";

import { ArToggle, InventoryPicker, fmtT, useInventories } from "./_lib";
import { OnboardingChecklist } from "./_onboarding";

export default function Scope1Dashboard() {
  const { inventories, active, activeId, setActiveId, loading } = useInventories();
  const [arVersion, setArVersion] = useState("AR5");
  const [report, setReport] = useState<S1Report | null>(null);
  const [readiness, setReadiness] = useState<S1Readiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = useCallback(async () => {
    if (!activeId) {
      setReport(null);
      setReadiness(null);
      return;
    }
    setError(null);
    try {
      const [rep, ready] = await Promise.all([
        scope1Api.report(activeId, arVersion),
        scope1Api.readiness(activeId),
      ]);
      setReport(rep);
      setReadiness(ready);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [activeId, arVersion]);

  useEffect(() => {
    void loadMetrics();
  }, [loadMetrics]);

  return (
    <div className="space-y-6">
      <ModuleIntro
        moduleKey="scope-1"
        icon={Flame}
        title="Scope 1 emissions"
        job="Build a standards-correct, audit-ready inventory of your direct combustion emissions."
        steps={[
          "Model your org, facilities and combustion sources",
          "Bring in fuel & fleet activity data with evidence",
          "Report per-gas totals (GHG Protocol / SB 253) and trace every number",
        ]}
        needs="Your legal entities, facilities, and fuel/fleet consumption for a reporting year."
      />

      <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Flame className="h-6 w-6 text-muted-foreground" />
            <h1 className="text-h1">Scope 1</h1>
          </div>
          <p className="mt-2 text-small text-muted-foreground">
            Direct emissions from owned and controlled combustion sources.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <InventoryPicker inventories={inventories} activeId={activeId} onChange={setActiveId} />
          <ArToggle value={arVersion} onChange={setArVersion} />
        </div>
      </section>

      <div className="flex flex-wrap gap-2">
        <Button asChild variant="outline">
          <Link href="/scope-1/setup">
            <Settings2 className="h-4 w-4" />
            Set up inventory
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/scope-1/collection">
            <ListChecks className="h-4 w-4" />
            Data collection
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/scope-1/data">
            <Database className="h-4 w-4" />
            Add activity data
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/scope-1/review">
            <ClipboardCheck className="h-4 w-4" />
            Review queue
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/scope-1/report">
            <FileText className="h-4 w-4" />
            Report &amp; trace
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/scope-1/settings">
            <Users className="h-4 w-4" />
            Team &amp; roles
          </Link>
        </Button>
      </div>

      <OnboardingChecklist />

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-3">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
      ) : inventories.length === 0 ? (
        <Alert>
          <AlertTitle>No inventory yet</AlertTitle>
          <AlertDescription>
            Create your first reporting-year inventory in{" "}
            <Link href="/scope-1/setup" className="font-medium underline-offset-4 hover:underline">
              Set up inventory
            </Link>
            .
          </AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <MetricCard
              label={`Gross Scope 1 (${arVersion})`}
              value={fmtT(report?.total_scope1_tco2e)}
              unit="tCO₂e"
              hint={active ? `${active.reporting_year} · ${report?.record_count ?? 0} record(s)` : undefined}
            />
            <MetricCard
              label="Biogenic CO₂ (memo)"
              value={fmtT(report?.biogenic_co2_tco2e)}
              unit="tCO₂e"
              hint="Separate line — excluded from the Scope 1 total"
            />
            <MetricCard
              label="Data readiness"
              value={readiness ? `${Math.round(readiness.completeness_pct)}%` : "—"}
              hint={readiness ? `${readiness.complete} of ${readiness.total} source-periods` : "No collection tracked yet"}
              footer={
                readiness && readiness.total > 0 ? (
                  <Progress value={readiness.completeness_pct} />
                ) : null
              }
            />
          </div>

          {report && report.by_gas.total_tco2e > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>By gas ({arVersion})</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-3">
                <MetricCard label="CO₂ (fossil)" value={fmtT(report.by_gas.co2_fossil_tco2e)} unit="tCO₂e" />
                <MetricCard label="CH₄" value={fmtT(report.by_gas.ch4_tco2e)} unit="tCO₂e" />
                <MetricCard label="N₂O" value={fmtT(report.by_gas.n2o_tco2e)} unit="tCO₂e" />
              </CardContent>
            </Card>
          ) : null}
        </>
      )}
    </div>
  );
}
