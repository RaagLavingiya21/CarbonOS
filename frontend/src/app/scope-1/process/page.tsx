"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Factory, Trash2 } from "lucide-react";

import { MetricCard } from "@/components/data/MetricCard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  scope1Api,
  type S1Process,
  type S1ProcessFactor,
} from "@/lib/scope1-api";

import { ArToggle, InventoryPicker, fmtT, useInventories } from "../_lib";

const GASES = ["Carbon dioxide", "Methane", "Nitrous oxide"];

export default function Scope1ProcessPage() {
  const { inventories, activeId, setActiveId, loading } = useInventories();
  const [arVersion, setArVersion] = useState("AR5");
  const [factors, setFactors] = useState<S1ProcessFactor[]>([]);
  const [data, setData] = useState<S1Process | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeId) {
      setData(null);
      return;
    }
    setError(null);
    try {
      setData(await scope1Api.process(activeId, arVersion));
    } catch (err) {
      setError((err as Error).message);
    }
  }, [activeId, arVersion]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    scope1Api.processFactors().then(setFactors).catch(() => setFactors([]));
  }, []);

  async function remove(id: string) {
    try {
      await scope1Api.deleteProcess(id);
      await load();
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
            <Factory className="h-6 w-6 text-muted-foreground" />
            <h1 className="text-h1">Process emissions</h1>
          </div>
          <p className="mt-2 text-small text-muted-foreground">
            Direct emissions from chemical / physical transformation (e.g. cement calcination,
            nitric acid) — Scope 1 alongside combustion and fugitive. We store the gas mass; tCO₂e
            derives from the gas GWP at the selected AR version.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <InventoryPicker inventories={inventories} activeId={activeId} onChange={setActiveId} />
          <ArToggle value={arVersion} onChange={setArVersion} />
        </div>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <p className="text-small text-muted-foreground">Loading…</p>
      ) : !activeId ? (
        <Alert>
          <AlertDescription>Select an inventory to record process emissions.</AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <MetricCard
              label={`Process total (${arVersion})`}
              value={fmtT(data?.total_tco2e)}
              unit="tCO₂e"
              hint={`${data?.records.length ?? 0} record(s)`}
            />
            <MetricCard
              label="Process types in library"
              value={String(factors.length)}
              hint="IPCC defaults + custom entry"
            />
          </div>

          <AddProcessCard
            inventoryId={activeId}
            factors={factors}
            onSaved={load}
            onError={setError}
          />

          <Card>
            <CardHeader>
              <CardTitle>Process records ({arVersion})</CardTitle>
              <CardDescription>tCO₂e = emitted gas kg × gas GWP ÷ 1000.</CardDescription>
            </CardHeader>
            <CardContent>
              {!data || data.records.length === 0 ? (
                <p className="text-small text-muted-foreground">No process records yet.</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="bg-secondary text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Process</th>
                        <th className="px-3 py-2">Gas</th>
                        <th className="px-3 py-2 text-right">Activity</th>
                        <th className="px-3 py-2 text-right">Gas kg</th>
                        <th className="px-3 py-2 text-right">tCO₂e</th>
                        <th className="px-3 py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.records.map((r) => (
                        <tr key={r.id} className="border-t bg-card">
                          <td className="px-3 py-2 font-medium">
                            {r.process_type}
                            {r.description ? (
                              <span className="ml-2 text-caption text-muted-foreground">{r.description}</span>
                            ) : null}
                          </td>
                          <td className="px-3 py-2 text-caption text-muted-foreground">{r.gas_species}</td>
                          <td className="px-3 py-2 text-right font-mono">
                            {r.activity_quantity}
                            <span className="ml-1 text-caption text-muted-foreground">{r.activity_unit}</span>
                          </td>
                          <td className="px-3 py-2 text-right font-mono">{r.emission_kg}</td>
                          <td className="px-3 py-2 text-right font-mono">{fmtT(r.tco2e)}</td>
                          <td className="px-3 py-2 text-right">
                            <Button type="button" size="sm" variant="ghost" onClick={() => remove(r.id)}>
                              <Trash2 className="h-4 w-4" />
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
        </>
      )}
    </div>
  );
}

function AddProcessCard({
  inventoryId,
  factors,
  onSaved,
  onError,
}: {
  inventoryId: string;
  factors: S1ProcessFactor[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [processType, setProcessType] = useState("custom");
  const [gas, setGas] = useState(GASES[0]);
  const [efValue, setEfValue] = useState("");
  const [activityQty, setActivityQty] = useState("");
  const [activityUnit, setActivityUnit] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const selected = useMemo(
    () => factors.find((f) => f.process_type === processType),
    [factors, processType],
  );
  const isCustom = processType === "custom";

  // Prefill from the library when a known process is chosen.
  function chooseProcess(pt: string) {
    setProcessType(pt);
    const f = factors.find((x) => x.process_type === pt);
    if (f) {
      setGas(f.gas);
      setEfValue(String(f.value));
      setActivityUnit(f.activity_unit);
    }
  }

  const ready = activityQty.trim() && efValue.trim() && (isCustom ? gas : true);

  async function submit() {
    if (!ready) return;
    setSaving(true);
    try {
      await scope1Api.createProcess({
        inventory_id: inventoryId,
        process_type: processType,
        gas_species: isCustom ? gas : selected?.gas ?? gas,
        activity_quantity: Number(activityQty),
        ef_value: Number(efValue),
        ...(activityUnit.trim() ? { activity_unit: activityUnit.trim() } : {}),
        ...(selected ? { ef_unit: selected.unit, ef_source: selected.source } : {}),
        ...(description.trim() ? { description: description.trim() } : {}),
      });
      setActivityQty("");
      setDescription("");
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Add a process record</CardTitle>
        <CardDescription>
          Emitted gas = activity × emission factor. Pick an IPCC default process (prefills the
          factor) or choose Custom to enter your own.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Process</Label>
            <select
              value={processType}
              onChange={(e) => chooseProcess(e.target.value)}
              className="h-10 w-full rounded-md border bg-card px-2 text-small"
            >
              {factors.map((f) => (
                <option key={f.process_type} value={f.process_type}>
                  {f.label}
                </option>
              ))}
              <option value="custom">Custom…</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Gas</Label>
            <select
              value={isCustom ? gas : selected?.gas ?? gas}
              onChange={(e) => setGas(e.target.value)}
              disabled={!isCustom}
              className="h-10 w-full rounded-md border bg-card px-2 text-small disabled:opacity-60"
            >
              {GASES.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Emission factor (kg gas / unit)</Label>
            <Input value={efValue} onChange={(e) => setEfValue(e.target.value)} inputMode="decimal" />
          </div>
          <div className="space-y-1.5">
            <Label>Activity quantity</Label>
            <Input value={activityQty} onChange={(e) => setActivityQty(e.target.value)} inputMode="decimal" />
          </div>
          <div className="space-y-1.5">
            <Label>Activity unit</Label>
            <Input value={activityUnit} onChange={(e) => setActivityUnit(e.target.value)} placeholder="t clinker" />
          </div>
          <div className="space-y-1.5">
            <Label>Description (optional)</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Kiln 2" />
          </div>
        </div>
        {selected ? (
          <p className="text-caption text-muted-foreground">Source: {selected.source}</p>
        ) : null}
        <div className="flex justify-end">
          <Button type="button" onClick={submit} disabled={saving || !ready}>
            Add record
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
