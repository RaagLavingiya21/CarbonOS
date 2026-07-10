"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Check, TrendingDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  InventoryVersion,
  ProgressResult,
  RecalcResult,
  scope3Api,
} from "@/lib/scope3-api";
import { formatKg } from "@/lib/utils";

function pct(n: number) {
  return `${n >= 0 ? "−" : "+"}${Math.abs(n).toFixed(1)}%`;
}

function Stat({ label, value, hint, accent }: { label: string; value: string; hint?: string; accent?: boolean }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-muted-foreground text-xs font-medium uppercase">{label}</p>
        <p className={`mt-1 font-mono text-xl font-semibold ${accent ? "text-green-600" : ""}`}>
          {value}
        </p>
        {hint && <p className="text-muted-foreground mt-0.5 text-xs">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export default function ProgressPage() {
  const [inventories, setInventories] = useState<InventoryVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tracking, setTracking] = useState(false);
  const [result, setResult] = useState<ProgressResult | null>(null);

  const [form, setForm] = useState({ baseId: "", currentId: "", targetTco2e: "" });

  const [recalc, setRecalc] = useState({ trigger: "structural change", significance: "", threshold: "5" });
  const [recalcResult, setRecalcResult] = useState<RecalcResult | null>(null);
  const [recalcRunning, setRecalcRunning] = useState(false);

  useEffect(() => {
    scope3Api
      .listInventories()
      .then((invs) => {
        setInventories(invs);
        setForm((f) => ({
          ...f,
          baseId: f.baseId || (invs[invs.length - 1] ? String(invs[invs.length - 1].inventory_id) : ""),
          currentId: f.currentId || (invs[0] ? String(invs[0].inventory_id) : ""),
        }));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load inventories."));
  }, []);

  const handleTrack = async () => {
    if (!form.baseId || !form.currentId) {
      setError("Pick a base and a current inventory.");
      return;
    }
    setTracking(true);
    setError(null);
    try {
      const currentInv = inventories.find((i) => String(i.inventory_id) === form.currentId);
      const trajectory: Record<string, number> = {};
      if (form.targetTco2e && currentInv) {
        trajectory[String(currentInv.reporting_year)] = Number(form.targetTco2e) * 1000;
      }
      setResult(
        await scope3Api.trackProgress({
          base_inventory_id: Number(form.baseId),
          current_inventory_id: Number(form.currentId),
          target_id: null,
          trajectory,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to track progress.");
    } finally {
      setTracking(false);
    }
  };

  const handleRecalc = async () => {
    setRecalcRunning(true);
    setError(null);
    try {
      setRecalcResult(
        await scope3Api.recalcCheck({
          trigger: recalc.trigger.trim() || "structural change",
          significance_pct: Number(recalc.significance || 0),
          threshold_pct: recalc.threshold ? Number(recalc.threshold) : null,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run recalc check.");
    } finally {
      setRecalcRunning(false);
    }
  };

  // derived splits
  const realReductionPct = result ? ((result.base_total_kg - result.real_total_kg) / result.base_total_kg) * 100 : 0;
  const actualReductionPct = result ? ((result.base_total_kg - result.actual_total_kg) / result.base_total_kg) * 100 : 0;
  const totalDrop = result ? result.base_total_kg - result.actual_total_kg : 0;
  const realDrop = result ? result.base_total_kg - result.real_total_kg : 0;
  const methodDrop = result ? result.real_total_kg - result.actual_total_kg : 0;
  const realShare = totalDrop > 0 ? Math.max(0, Math.min(100, (realDrop / totalDrop) * 100)) : 0;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Progress</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Track like-for-like reductions vs your target — real cuts separated from method
            changes.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Compare inventories</CardTitle>
          <CardDescription>Base vs current year, with an optional target for the current year.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div>
            <Label htmlFor="base">Base inventory</Label>
            <Select value={form.baseId} onValueChange={(v) => setForm({ ...form, baseId: v })}>
              <SelectTrigger id="base"><SelectValue placeholder="Base" /></SelectTrigger>
              <SelectContent>
                {inventories.map((i) => (
                  <SelectItem key={i.inventory_id} value={String(i.inventory_id)}>
                    {i.reporting_year} · {i.status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="current">Current inventory</Label>
            <Select value={form.currentId} onValueChange={(v) => setForm({ ...form, currentId: v })}>
              <SelectTrigger id="current"><SelectValue placeholder="Current" /></SelectTrigger>
              <SelectContent>
                {inventories.map((i) => (
                  <SelectItem key={i.inventory_id} value={String(i.inventory_id)}>
                    {i.reporting_year} · {i.status}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="target">Target for current year (tCO₂e)</Label>
            <Input
              id="target"
              type="number"
              placeholder="optional"
              value={form.targetTco2e}
              onChange={(e) => setForm({ ...form, targetTco2e: e.target.value })}
            />
          </div>
          <div className="sm:col-span-3">
            <Button onClick={handleTrack} disabled={tracking}>
              {tracking ? "Tracking..." : "Track progress"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-6">
          {/* hero */}
          <div
            className={`flex items-center gap-4 rounded-lg border p-5 ${
              result.on_track === true
                ? "border-green-600/30 bg-green-600/5"
                : result.on_track === false
                  ? "border-destructive/30 bg-destructive/5"
                  : "border-border bg-muted/30"
            }`}
          >
            {result.on_track === true && (
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-green-600 text-green-600">
                <Check className="h-5 w-5" />
              </span>
            )}
            <div>
              <p
                className={`text-lg font-semibold ${
                  result.on_track === true
                    ? "text-green-600"
                    : result.on_track === false
                      ? "text-destructive"
                      : ""
                }`}
              >
                {result.on_track === true
                  ? "On track"
                  : result.on_track === false
                    ? "Off track"
                    : "No target set"}
              </p>
              <p className="text-muted-foreground text-sm">
                Reporting year {result.current_year} · like-for-like vs base
              </p>
            </div>
          </div>

          {/* KPIs */}
          <div className="grid gap-3 sm:grid-cols-4">
            <Stat label="Base" value={formatKg(result.base_total_kg)} />
            <Stat label="Actual" value={formatKg(result.actual_total_kg)} />
            <Stat
              label="Target"
              value={result.trajectory_target_kg != null ? formatKg(result.trajectory_target_kg) : "—"}
            />
            <Stat label="Real reduction" value={pct(realReductionPct)} accent hint={`actual ${pct(actualReductionPct)}`} />
          </div>

          {/* split bar */}
          {totalDrop > 0 && (
            <Card>
              <CardContent className="py-4">
                <div className="mb-2 flex items-baseline justify-between">
                  <p className="text-muted-foreground text-xs font-medium uppercase">
                    Where the {formatKg(totalDrop)} drop came from
                  </p>
                </div>
                <div className="flex h-6 overflow-hidden rounded border border-border">
                  <div className="bg-green-600/80" style={{ width: `${realShare}%` }} title="Real reduction" />
                  <div className="bg-muted" style={{ width: `${100 - realShare}%` }} title="Method change" />
                </div>
                <div className="text-muted-foreground mt-2 flex gap-5 text-xs">
                  <span>
                    <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-green-600/80 align-middle" />
                    Real · {formatKg(realDrop)}
                  </span>
                  <span>
                    <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-sm bg-muted align-middle" />
                    Method · {formatKg(Math.abs(methodDrop))}
                  </span>
                </div>
              </CardContent>
            </Card>
          )}

          {result.notes.map((n, i) => (
            <div
              key={i}
              className="rounded-md border border-border border-l-2 border-l-green-600 bg-muted/30 px-4 py-3 text-sm text-muted-foreground"
            >
              {n}
            </div>
          ))}

          {/* recalc */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Base-year recalculation check</CardTitle>
              <CardDescription>
                Did a structural change cross the significance threshold and require restating the
                base year?
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <Label htmlFor="trigger">Trigger</Label>
                  <Input
                    id="trigger"
                    value={recalc.trigger}
                    onChange={(e) => setRecalc({ ...recalc, trigger: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="sig">Significance %</Label>
                  <Input
                    id="sig"
                    type="number"
                    value={recalc.significance}
                    onChange={(e) => setRecalc({ ...recalc, significance: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="thr">Threshold %</Label>
                  <Input
                    id="thr"
                    type="number"
                    value={recalc.threshold}
                    onChange={(e) => setRecalc({ ...recalc, threshold: e.target.value })}
                  />
                </div>
              </div>
              <Button variant="outline" onClick={handleRecalc} disabled={recalcRunning}>
                {recalcRunning ? "Checking..." : "Run recalc check"}
              </Button>
              {recalcResult && (
                <div className="rounded-md border border-border bg-muted/30 p-4 text-sm">
                  <div className="mb-2 flex items-center justify-between">
                    <span className="text-muted-foreground">{recalcResult.trigger}</span>
                    <Badge variant={recalcResult.recalc_required ? "medium" : "high"}>
                      {recalcResult.recalc_required ? "Restatement required" : "No restatement"}
                    </Badge>
                  </div>
                  <div className="text-muted-foreground flex gap-6 font-mono text-xs">
                    <span>significance {recalcResult.significance_pct}%</span>
                    <span>threshold {recalcResult.threshold_pct}%</span>
                  </div>
                  <p className="text-muted-foreground mt-2 text-xs">{recalcResult.rationale}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {!result && (
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <TrendingDown className="h-4 w-4" /> Pick two inventories and track to see progress.
        </div>
      )}
    </div>
  );
}
