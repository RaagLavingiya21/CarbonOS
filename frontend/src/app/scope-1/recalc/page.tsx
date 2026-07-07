"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, RefreshCcw, Trash2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MetricCard } from "@/components/data/MetricCard";
import { scope1Api, type S1Recalc } from "@/lib/scope1-api";

import { InventoryPicker, fmtT, useInventories } from "../_lib";

const TRIGGERS: { value: string; label: string; structural: boolean }[] = [
  { value: "acquisition", label: "Acquisition", structural: true },
  { value: "divestiture", label: "Divestiture", structural: true },
  { value: "outsourcing", label: "Outsourcing", structural: true },
  { value: "insourcing", label: "Insourcing", structural: true },
  { value: "methodology_change", label: "Methodology change", structural: true },
  { value: "error_correction", label: "Error correction", structural: true },
  { value: "organic_growth", label: "Organic growth", structural: false },
  { value: "organic_decline", label: "Organic decline", structural: false },
];

const LABELS = Object.fromEntries(TRIGGERS.map((t) => [t.value, t.label]));

export default function Scope1RecalcPage() {
  const { inventories, activeId, setActiveId, loading } = useInventories();
  const [data, setData] = useState<S1Recalc | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeId) {
      setData(null);
      return;
    }
    setError(null);
    try {
      setData(await scope1Api.recalc(activeId));
    } catch (err) {
      setError((err as Error).message);
    }
  }, [activeId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function apply() {
    if (!activeId) return;
    try {
      setData(await scope1Api.applyRecalc(activeId));
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function removeEvent(eventId: string) {
    if (!activeId) return;
    try {
      setData(await scope1Api.deleteRecalcEvent(activeId, eventId));
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
          <div className="flex items-center gap-2">
            <RefreshCcw className="h-6 w-6 text-muted-foreground" />
            <h1 className="text-h1">Base-year recalculation</h1>
          </div>
          <p className="mt-2 text-small text-muted-foreground">
            GHG Protocol: structural changes (M&amp;A, out/insourcing, methodology fixes) restate
            the base year so it stays comparable. Organic growth/decline never does.
          </p>
        </div>
        <InventoryPicker inventories={inventories} activeId={activeId} onChange={setActiveId} />
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <p className="text-small text-muted-foreground">Loading…</p>
      ) : !data ? (
        <Alert>
          <AlertDescription>Select an inventory to review its base-year recalculation.</AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <MetricCard
              label={`Base year ${data.base_year ?? ""} (current)`}
              value={fmtT(data.base_year_total_tco2e)}
              unit="tCO₂e"
              hint={
                data.significance_threshold_pct != null
                  ? `Significance threshold ${data.significance_threshold_pct}%`
                  : "No significance threshold declared"
              }
            />
            <MetricCard
              label="Pending structural change"
              value={fmtT(data.structural_delta_pending)}
              unit="tCO₂e"
              hint={data.pct_impact != null ? `${data.pct_impact.toFixed(1)}% of base year` : "—"}
            />
            <MetricCard
              label="Restated base year"
              value={fmtT(data.restated_total)}
              unit="tCO₂e"
              hint={data.organic_delta ? `Organic (excluded): ${fmtT(data.organic_delta)}` : undefined}
              footer={
                data.recalc_required === true ? (
                  <Badge variant="default">Recalculation required</Badge>
                ) : data.recalc_required === false ? (
                  <Badge variant="neutral">Below threshold</Badge>
                ) : data.has_pending ? (
                  <Badge variant="info">Threshold not declared</Badge>
                ) : null
              }
            />
          </div>

          {data.has_pending ? (
            <div className="flex items-center gap-3 rounded-md border bg-secondary/40 px-3 py-2">
              <span className="text-small">
                Apply the pending structural change to restate the base-year total to{" "}
                <span className="font-medium">{fmtT(data.restated_total)} tCO₂e</span>. This is logged
                to the audit trail.
              </span>
              <Button type="button" size="sm" onClick={apply} className="ml-auto">
                Apply recalculation
              </Button>
            </div>
          ) : null}

          <AddEventCard inventoryId={data.inventory_id} onSaved={setData} onError={setError} />

          <Card>
            <CardHeader>
              <CardTitle>Change events</CardTitle>
              <CardDescription>Structural changes restate the base year; organic ones are informational.</CardDescription>
            </CardHeader>
            <CardContent>
              {data.events.length === 0 ? (
                <p className="text-small text-muted-foreground">No change events recorded.</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="bg-secondary text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Trigger</th>
                        <th className="px-3 py-2">Description</th>
                        <th className="px-3 py-2 text-right">Δ tCO₂e</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.events.map((e) => (
                        <tr key={e.id} className="border-t bg-card">
                          <td className="px-3 py-2">
                            {LABELS[e.trigger_type] ?? e.trigger_type}
                            <Badge variant={e.is_structural ? "info" : "neutral"} className="ml-2">
                              {e.is_structural ? "structural" : "organic"}
                            </Badge>
                          </td>
                          <td className="px-3 py-2 text-caption text-muted-foreground">{e.description ?? "—"}</td>
                          <td className="px-3 py-2 text-right font-mono">
                            {e.delta_tco2e > 0 ? "+" : ""}
                            {e.delta_tco2e}
                          </td>
                          <td className="px-3 py-2">
                            {e.applied ? (
                              <Badge variant="neutral">applied</Badge>
                            ) : (
                              <span className="text-caption text-muted-foreground">pending</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-right">
                            {!e.applied ? (
                              <Button type="button" size="sm" variant="ghost" onClick={() => removeEvent(e.id)}>
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            ) : null}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function AddEventCard({
  inventoryId,
  onSaved,
  onError,
}: {
  inventoryId: string;
  onSaved: (data: S1Recalc) => void;
  onError: (message: string) => void;
}) {
  const [trigger, setTrigger] = useState(TRIGGERS[0].value);
  const [delta, setDelta] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!delta.trim()) return;
    setSaving(true);
    try {
      const data = await scope1Api.addRecalcEvent(inventoryId, {
        trigger_type: trigger,
        delta_tco2e: Number(delta),
        ...(description.trim() ? { description: description.trim() } : {}),
      });
      onSaved(data);
      setDelta("");
      setDescription("");
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Record a change event</CardTitle>
        <CardDescription>
          Δ is the base-year emissions to add (+) or remove (−): e.g. an acquired unit&apos;s base-year
          emissions, or a signed methodology/error correction.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-1.5">
            <Label>Trigger</Label>
            <select
              value={trigger}
              onChange={(e) => setTrigger(e.target.value)}
              className="h-10 w-full rounded-md border bg-card px-2 text-small"
            >
              <optgroup label="Structural (recalculates)">
                {TRIGGERS.filter((t) => t.structural).map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </optgroup>
              <optgroup label="Organic (no recalc)">
                {TRIGGERS.filter((t) => !t.structural).map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </optgroup>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Δ tCO₂e (signed)</Label>
            <Input value={delta} onChange={(e) => setDelta(e.target.value)} placeholder="80 or -120" inputMode="decimal" />
          </div>
          <div className="space-y-1.5 lg:col-span-2">
            <Label>Description</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Acquired Acme Foods (2020 base-year emissions)" />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <Button type="button" onClick={submit} disabled={saving || !delta.trim()}>
            Add event
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
