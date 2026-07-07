"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Beaker, Trash2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { scope1Api, type S1Factor } from "@/lib/scope1-api";

const GASES = ["CO2", "CH4", "N2O"];
const BASES = ["custom", "supplier", "measured"];
const CATEGORIES = ["stationary_combustion", "mobile_onroad", "mobile_nonroad"];

export default function Scope1FactorsPage() {
  const [factors, setFactors] = useState<S1Factor[]>([]);
  const [yourRole, setYourRole] = useState("viewer");
  const [overrideCount, setOverrideCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await scope1Api.factors();
      setFactors(data.factors);
      setYourRole(data.your_role);
      setOverrideCount(data.override_count);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isAdmin = yourRole === "admin";

  async function retire(overrideId: string) {
    try {
      await scope1Api.retireFactorOverride(overrideId);
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

      <div>
        <div className="flex items-center gap-2">
          <Beaker className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-h1">Emission factors</h1>
        </div>
        <p className="mt-2 text-small text-muted-foreground">
          The canonical EPA factor set. Admins can override a factor for this org — to
          early-adopt a new EPA year or record a measured/supplier-specific value — without
          changing the shared reference data. Overrides are versioned; retiring one restores
          the EPA factor.
          {!isAdmin ? " You have read-only access to this page." : ""}
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {isAdmin ? <OverrideCard onSaved={load} onError={setError} /> : null}

      <Card>
        <CardHeader>
          <CardTitle>Active factors</CardTitle>
          <CardDescription>
            {overrideCount} org override{overrideCount === 1 ? "" : "s"} · CO₂e is derived at
            reporting time (never stored)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-small text-muted-foreground">Loading…</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-secondary text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">Fuel / activity</th>
                    <th className="px-3 py-2">Category</th>
                    <th className="px-3 py-2">Gas</th>
                    <th className="px-3 py-2 text-right">Value</th>
                    <th className="px-3 py-2">Unit</th>
                    <th className="px-3 py-2">Source</th>
                    {isAdmin ? <th className="px-3 py-2"></th> : null}
                  </tr>
                </thead>
                <tbody>
                  {factors.map((f, i) => (
                    <tr
                      key={`${f.fuel_or_activity}-${f.source_category}-${f.gas}-${f.model_year ?? ""}-${i}`}
                      className="border-t bg-card"
                    >
                      <td className="px-3 py-2 font-medium">
                        {f.fuel_or_activity}
                        {f.is_override ? (
                          <Badge variant="default" className="ml-2">
                            override
                          </Badge>
                        ) : null}
                      </td>
                      <td className="px-3 py-2 text-caption text-muted-foreground">
                        {f.source_category}
                        {f.model_year ? ` · MY${f.model_year}` : ""}
                      </td>
                      <td className="px-3 py-2">{f.gas}</td>
                      <td className="px-3 py-2 text-right font-mono">{f.value}</td>
                      <td className="px-3 py-2 text-caption text-muted-foreground">{f.unit}</td>
                      <td className="px-3 py-2 text-caption text-muted-foreground">
                        {f.source} <span className="opacity-60">({f.source_version})</span>
                      </td>
                      {isAdmin ? (
                        <td className="px-3 py-2 text-right">
                          {f.is_override && f.override_id ? (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={() => retire(f.override_id as string)}
                            >
                              <Trash2 className="h-4 w-4" />
                              Retire
                            </Button>
                          ) : null}
                        </td>
                      ) : null}
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

function OverrideCard({
  onSaved,
  onError,
}: {
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [form, setForm] = useState({
    fuel_or_activity: "",
    source_category: CATEGORIES[0],
    gas: GASES[0],
    value: "",
    unit: "kg/mmBtu",
    source: "",
    source_version: "",
    basis: BASES[0],
    model_year: "",
  });
  const [saving, setSaving] = useState(false);

  function set<K extends keyof typeof form>(key: K, v: string) {
    setForm((f) => ({ ...f, [key]: v }));
  }

  const ready =
    form.fuel_or_activity.trim() &&
    form.value.trim() &&
    form.unit.trim() &&
    form.source.trim() &&
    form.source_version.trim();

  async function submit() {
    if (!ready) return;
    setSaving(true);
    try {
      await scope1Api.createFactorOverride({
        fuel_or_activity: form.fuel_or_activity.trim(),
        source_category: form.source_category,
        gas: form.gas,
        value: Number(form.value),
        unit: form.unit.trim(),
        source: form.source.trim(),
        source_version: form.source_version.trim(),
        basis: form.basis,
        ...(form.model_year.trim() ? { model_year: Number(form.model_year) } : {}),
      });
      setForm((f) => ({ ...f, fuel_or_activity: "", value: "", source: "", source_version: "" }));
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
        <CardTitle>Override a factor</CardTitle>
        <CardDescription>
          Replaces the EPA factor for the matching fuel / category / gas (and model year, for
          mobile) for this org only.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Fuel / activity</Label>
            <Input
              value={form.fuel_or_activity}
              onChange={(e) => set("fuel_or_activity", e.target.value)}
              placeholder="natural_gas"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Category</Label>
            <SelectBox value={form.source_category} options={CATEGORIES} onChange={(v) => set("source_category", v)} />
          </div>
          <div className="space-y-1.5">
            <Label>Gas</Label>
            <SelectBox value={form.gas} options={GASES} onChange={(v) => set("gas", v)} />
          </div>
          <div className="space-y-1.5">
            <Label>Value</Label>
            <Input value={form.value} onChange={(e) => set("value", e.target.value)} placeholder="52.91" inputMode="decimal" />
          </div>
          <div className="space-y-1.5">
            <Label>Unit</Label>
            <Input value={form.unit} onChange={(e) => set("unit", e.target.value)} placeholder="kg/mmBtu" />
          </div>
          <div className="space-y-1.5">
            <Label>Basis</Label>
            <SelectBox value={form.basis} options={BASES} onChange={(v) => set("basis", v)} />
          </div>
          <div className="space-y-1.5">
            <Label>Source</Label>
            <Input value={form.source} onChange={(e) => set("source", e.target.value)} placeholder="EPA EF Hub 2026" />
          </div>
          <div className="space-y-1.5">
            <Label>Source version</Label>
            <Input value={form.source_version} onChange={(e) => set("source_version", e.target.value)} placeholder="2026-01-15" />
          </div>
          <div className="space-y-1.5">
            <Label>Model year (mobile, optional)</Label>
            <Input value={form.model_year} onChange={(e) => set("model_year", e.target.value)} placeholder="" inputMode="numeric" />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <Button type="button" onClick={submit} disabled={saving || !ready}>
            Publish override
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SelectBox({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-10 w-full rounded-md border bg-card px-2 text-small"
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
