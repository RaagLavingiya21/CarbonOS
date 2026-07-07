"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Snowflake, Trash2 } from "lucide-react";

import { MetricCard } from "@/components/data/MetricCard";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  scope1Api,
  type S1Fugitive,
  type S1Refrigerant,
} from "@/lib/scope1-api";

import { ArToggle, InventoryPicker, fmtT, useInventories } from "../_lib";

export default function Scope1FugitivePage() {
  const { inventories, activeId, setActiveId, loading } = useInventories();
  const [arVersion, setArVersion] = useState("AR5");
  const [refrigerants, setRefrigerants] = useState<S1Refrigerant[]>([]);
  const [data, setData] = useState<S1Fugitive | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!activeId) {
      setData(null);
      return;
    }
    setError(null);
    try {
      setData(await scope1Api.fugitive(activeId, arVersion));
    } catch (err) {
      setError((err as Error).message);
    }
  }, [activeId, arVersion]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    scope1Api.refrigerants().then(setRefrigerants).catch(() => setRefrigerants([]));
  }, []);

  async function remove(id: string) {
    try {
      await scope1Api.deleteFugitive(id);
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
            <Snowflake className="h-6 w-6 text-muted-foreground" />
            <h1 className="text-h1">Fugitive emissions</h1>
          </div>
          <p className="mt-2 text-small text-muted-foreground">
            Refrigerant leakage from AC / refrigeration — a Scope 1 source alongside combustion.
            We store the leaked mass; tCO₂e is derived from the refrigerant GWP at the selected AR
            version.
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
          <AlertDescription>Select an inventory to record fugitive emissions.</AlertDescription>
        </Alert>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <MetricCard
              label={`Fugitive total (${arVersion})`}
              value={fmtT(data?.total_tco2e)}
              unit="tCO₂e"
              hint={`${data?.records.length ?? 0} record(s)`}
            />
            <MetricCard
              label="Refrigerants in library"
              value={String(refrigerants.length)}
              hint="Pure species + common blends, GWP by AR version"
            />
          </div>

          <AddFugitiveCard
            inventoryId={activeId}
            refrigerants={refrigerants}
            onSaved={load}
            onError={setError}
          />

          <Card>
            <CardHeader>
              <CardTitle>Fugitive records ({arVersion})</CardTitle>
              <CardDescription>tCO₂e = leaked kg × refrigerant GWP ÷ 1000.</CardDescription>
            </CardHeader>
            <CardContent>
              {!data || data.records.length === 0 ? (
                <p className="text-small text-muted-foreground">No fugitive records yet.</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border">
                  <table className="w-full min-w-[680px] text-left text-sm">
                    <thead className="bg-secondary text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Refrigerant</th>
                        <th className="px-3 py-2">Method</th>
                        <th className="px-3 py-2 text-right">Leaked kg</th>
                        <th className="px-3 py-2 text-right">GWP</th>
                        <th className="px-3 py-2 text-right">tCO₂e</th>
                        <th className="px-3 py-2"></th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.records.map((r) => (
                        <tr key={r.id} className="border-t bg-card">
                          <td className="px-3 py-2 font-medium">
                            {r.refrigerant}
                            {r.description ? (
                              <span className="ml-2 text-caption text-muted-foreground">{r.description}</span>
                            ) : null}
                          </td>
                          <td className="px-3 py-2 text-caption text-muted-foreground">
                            {r.method === "material_balance" ? "material balance" : "screening"}
                          </td>
                          <td className="px-3 py-2 text-right font-mono">{r.leaked_kg}</td>
                          <td className="px-3 py-2 text-right font-mono">{r.gwp}</td>
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

function AddFugitiveCard({
  inventoryId,
  refrigerants,
  onSaved,
  onError,
}: {
  inventoryId: string;
  refrigerants: S1Refrigerant[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [refrigerant, setRefrigerant] = useState("");
  const [method, setMethod] = useState("screening");
  const [charge, setCharge] = useState("");
  const [leakRate, setLeakRate] = useState("");
  const [purchases, setPurchases] = useState("");
  const [beginning, setBeginning] = useState("");
  const [ending, setEnding] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const effRefrigerant = refrigerant || refrigerants[0]?.name || "";

  const ready =
    effRefrigerant &&
    (method === "screening"
      ? charge.trim() && leakRate.trim()
      : purchases.trim() && beginning.trim() && ending.trim());

  async function submit() {
    if (!ready) return;
    setSaving(true);
    try {
      await scope1Api.createFugitive({
        inventory_id: inventoryId,
        refrigerant: effRefrigerant,
        method,
        ...(method === "screening"
          ? { charge_kg: Number(charge), leak_rate_pct: Number(leakRate) }
          : {
              purchases_kg: Number(purchases),
              beginning_inventory_kg: Number(beginning),
              ending_inventory_kg: Number(ending),
            }),
        ...(description.trim() ? { description: description.trim() } : {}),
      });
      setCharge("");
      setLeakRate("");
      setPurchases("");
      setBeginning("");
      setEnding("");
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
        <CardTitle>Add a fugitive record</CardTitle>
        <CardDescription>
          Screening = charge × annual leak rate. Material balance = purchases + start stock − end
          stock (refrigerant added to top up a system ≈ what leaked).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Refrigerant</Label>
            <select
              value={effRefrigerant}
              onChange={(e) => setRefrigerant(e.target.value)}
              className="h-10 w-full rounded-md border bg-card px-2 text-small"
            >
              {refrigerants.map((r) => (
                <option key={r.name} value={r.name}>
                  {r.name} (GWP {r.gwp.AR5})
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Method</Label>
            <div className="flex rounded-md border p-0.5">
              {["screening", "material_balance"].map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMethod(m)}
                  className={`flex-1 rounded px-2 py-1.5 text-small ${
                    method === m ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                  }`}
                >
                  {m === "material_balance" ? "Material balance" : "Screening"}
                </button>
              ))}
            </div>
          </div>
          <div className="space-y-1.5 lg:col-span-1">
            <Label>Description (optional)</Label>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Rooftop chillers" />
          </div>
        </div>

        {method === "screening" ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <FugInput label="Refrigerant charge (kg)" value={charge} onChange={setCharge} />
            <FugInput label="Annual leak rate (%)" value={leakRate} onChange={setLeakRate} />
          </div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <FugInput label="Purchases / top-ups (kg)" value={purchases} onChange={setPurchases} />
            <FugInput label="Beginning stock (kg)" value={beginning} onChange={setBeginning} />
            <FugInput label="Ending stock (kg)" value={ending} onChange={setEnding} />
          </div>
        )}

        <div className="flex justify-end">
          <Button type="button" onClick={submit} disabled={saving || !ready}>
            Add record
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function FugInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <Input value={value} onChange={(e) => onChange(e.target.value)} inputMode="decimal" />
    </div>
  );
}
