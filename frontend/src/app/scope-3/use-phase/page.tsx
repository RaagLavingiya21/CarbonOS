"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Trash2, Zap } from "lucide-react";

import { Button } from "@/components/ui/button";
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
import { UsePhasePayload, UsePhaseResult, scope3Api } from "@/lib/scope3-api";
import { formatKg } from "@/lib/utils";

const SEGMENT_COLORS = ["hsl(var(--primary))", "#16a34a", "#0ea5e9", "#f59e0b", "#a855f7"];

function prettyKey(k: string) {
  return k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export default function UsePhasePage() {
  const [error, setError] = useState<string | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [result, setResult] = useState<UsePhaseResult | null>(null);
  const [specs, setSpecs] = useState<Record<string, unknown>[]>([]);

  const [form, setForm] = useState({
    product_ref: "",
    units_sold: "",
    region: "",
    energy_per_use_kwh: "",
    water_l_per_use: "",
    standby_power_w: "",
    fuel_kwh_per_use: "",
    uses_per_year: "",
    lifetime_years: "",
    mode: "direct",
    include_standby: true,
  });

  const loadSpecs = async () => {
    try {
      setSpecs(await scope3Api.listSpecs());
    } catch {
      /* specs list is best-effort */
    }
  };

  useEffect(() => {
    loadSpecs();
  }, []);

  const payload = (): UsePhasePayload => ({
    product_ref: form.product_ref.trim() || "product",
    energy_per_use_kwh: Number(form.energy_per_use_kwh || 0),
    water_l_per_use: Number(form.water_l_per_use || 0),
    standby_power_w: Number(form.standby_power_w || 0),
    fuel_kwh_per_use: Number(form.fuel_kwh_per_use || 0),
    uses_per_year: Number(form.uses_per_year || 0),
    lifetime_years: Number(form.lifetime_years || 0),
    units_sold: Number(form.units_sold || 0),
    region: form.region.trim() || null,
    mode: form.mode,
    include_standby: form.include_standby,
  });

  const handleCalc = async () => {
    setCalculating(true);
    setError(null);
    try {
      setResult(await scope3Api.calcUsePhase(payload()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to calculate.");
    } finally {
      setCalculating(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await scope3Api.createSpec(payload());
      await loadSpecs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save spec.");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSpec = async (id: number) => {
    try {
      await scope3Api.deleteSpec(id);
      await loadSpecs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete spec.");
    }
  };

  const breakdown = result ? Object.entries(result.breakdown).filter(([, v]) => v > 0) : [];
  const breakdownTotal = breakdown.reduce((s, [, v]) => s + v, 0) || 1;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Use-phase calculator</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Category 11 — lifetime emissions from customers using your sold products.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {/* Inputs */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Inputs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="pref">Product</Label>
                <Input id="pref" value={form.product_ref} onChange={(e) => setForm({ ...form, product_ref: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="units">Units sold</Label>
                <Input id="units" type="number" value={form.units_sold} onChange={(e) => setForm({ ...form, units_sold: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="energy">Energy / use (kWh)</Label>
                <Input id="energy" type="number" value={form.energy_per_use_kwh} onChange={(e) => setForm({ ...form, energy_per_use_kwh: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="water">Water / use (L)</Label>
                <Input id="water" type="number" value={form.water_l_per_use} onChange={(e) => setForm({ ...form, water_l_per_use: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="standby">Standby (W)</Label>
                <Input id="standby" type="number" value={form.standby_power_w} onChange={(e) => setForm({ ...form, standby_power_w: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="fuel">Fuel / use (kWh)</Label>
                <Input id="fuel" type="number" value={form.fuel_kwh_per_use} onChange={(e) => setForm({ ...form, fuel_kwh_per_use: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="uses">Uses / year</Label>
                <Input id="uses" type="number" value={form.uses_per_year} onChange={(e) => setForm({ ...form, uses_per_year: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="life">Lifetime (yrs)</Label>
                <Input id="life" type="number" value={form.lifetime_years} onChange={(e) => setForm({ ...form, lifetime_years: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="region">Region</Label>
                <Input id="region" placeholder="optional" value={form.region} onChange={(e) => setForm({ ...form, region: e.target.value })} />
              </div>
              <div>
                <Label htmlFor="mode">Mode</Label>
                <Select value={form.mode} onValueChange={(v) => setForm({ ...form, mode: v })}>
                  <SelectTrigger id="mode"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="direct">Direct</SelectItem>
                    <SelectItem value="indirect">Indirect</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4" checked={form.include_standby} onChange={(e) => setForm({ ...form, include_standby: e.currentTarget.checked })} />
              Include standby consumption
            </label>
            <Button onClick={handleCalc} disabled={calculating} className="w-full">
              {calculating ? "Calculating..." : "Calculate Category 11"}
            </Button>
          </CardContent>
        </Card>

        {/* Result */}
        <Card className="bg-muted/30">
          <CardHeader>
            <CardTitle className="text-base">Result</CardTitle>
            <CardDescription>{result ? result.product_name : "Calculate to see the result"}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!result ? (
              <p className="text-muted-foreground text-sm">Fill in the inputs and press <b>Calculate</b>.</p>
            ) : (
              <>
                <div>
                  <p className="font-mono text-3xl font-semibold">{formatKg(result.kg_co2e)}</p>
                  <p className="text-muted-foreground text-xs">
                    {result.units_sold.toLocaleString()} units · {result.direct_or_indirect} · method {result.method}
                  </p>
                </div>

                <div className="space-y-1.5 text-sm">
                  <div className="flex justify-between border-b border-border py-1">
                    <span className="text-muted-foreground">EF source</span>
                    <span className="font-mono text-xs">{result.ef_source}</span>
                  </div>
                </div>
                <p className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                  {result.dq_note}
                </p>

                {breakdown.length > 0 && (
                  <div>
                    <p className="text-muted-foreground text-xs font-medium uppercase">Contributors</p>
                    <div className="mt-1 flex h-6 overflow-hidden rounded border border-border">
                      {breakdown.map(([k, v], i) => (
                        <div
                          key={k}
                          style={{ width: `${(v / breakdownTotal) * 100}%`, background: SEGMENT_COLORS[i % SEGMENT_COLORS.length] }}
                          title={`${prettyKey(k)}: ${formatKg(v)}`}
                        />
                      ))}
                    </div>
                    <div className="mt-2 space-y-1">
                      {breakdown.map(([k, v], i) => (
                        <div key={k} className="flex items-center gap-2 text-xs">
                          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SEGMENT_COLORS[i % SEGMENT_COLORS.length] }} />
                          <span className="text-muted-foreground">{prettyKey(k)}</span>
                          <span className="ml-auto font-mono">{formatKg(v)}</span>
                          <span className="text-muted-foreground w-10 text-right font-mono">
                            {((v / breakdownTotal) * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <Button variant="outline" onClick={handleSave} disabled={saving} className="w-full">
                  {saving ? "Saving..." : "Save spec"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Saved specs */}
      {specs.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-3 text-sm font-semibold tracking-tight">Saved specs</h2>
          <Card className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left">
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Product</th>
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Region</th>
                  <th className="px-4 py-2.5 text-right text-xs font-medium uppercase text-muted-foreground">Units</th>
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Mode</th>
                  <th className="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody>
                {specs.map((s, i) => (
                  <tr key={(s.spec_id as number) ?? i} className="border-b border-border last:border-0">
                    <td className="px-4 py-2.5 font-medium">{String(s.product_ref ?? "—")}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{String(s.region ?? "—")}</td>
                    <td className="px-4 py-2.5 text-right font-mono">{Number(s.units_sold ?? 0).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-muted-foreground">{String(s.mode ?? "—")}</td>
                    <td className="px-4 py-2.5 text-right">
                      {s.spec_id != null && (
                        <button
                          type="button"
                          onClick={() => handleDeleteSpec(s.spec_id as number)}
                          className="text-muted-foreground hover:text-destructive"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {!result && specs.length === 0 && (
        <div className="text-muted-foreground mt-6 flex items-center gap-2 text-sm">
          <Zap className="h-4 w-4" /> Enter a product profile and calculate its use-phase footprint.
        </div>
      )}
    </div>
  );
}
