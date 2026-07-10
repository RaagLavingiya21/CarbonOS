"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, Plus, Trash2, Users } from "lucide-react";

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
import { Skeleton } from "@/components/ui/skeleton";
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
  Cohort,
  Supplier,
  SupplierScorecard,
  scope3Api,
  SCOPE3_CATEGORY_NAMES,
} from "@/lib/scope3-api";
import { formatKg } from "@/lib/utils";

const ALL_CATEGORIES = Array.from({ length: 15 }, (_, i) => i + 1);
const SBT_STATUSES = ["none", "committed", "validated"];

function sbtVariant(status: string) {
  if (status === "validated") return "high" as const;
  if (status === "committed") return "info" as const;
  return "neutral" as const;
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <CardContent className="py-4">
        <p className="text-muted-foreground text-xs font-medium uppercase">{label}</p>
        <p className="mt-1 font-mono text-xl font-semibold">{value}</p>
        {hint && <p className="text-muted-foreground mt-0.5 text-xs">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export default function SuppliersPage() {
  const [suppliers, setSuppliers] = useState<Supplier[] | null>(null);
  const [scorecard, setScorecard] = useState<SupplierScorecard | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    name: "",
    category: "1",
    emissions: "",
    spend: "",
    pcf: false,
    dq: "",
    sbt: "none",
  });

  const [hotspots, setHotspots] = useState<number[]>([]);
  const [basis, setBasis] = useState("emissions");
  const [topN, setTopN] = useState("5");
  const [cohort, setCohort] = useState<Cohort | null>(null);
  const [buildingCohort, setBuildingCohort] = useState(false);

  const load = async () => {
    try {
      const [sup, sc] = await Promise.all([
        scope3Api.listSuppliers(),
        scope3Api.supplierScorecard().catch(() => null),
      ]);
      setSuppliers(sup);
      setScorecard(sc);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load suppliers.");
      setSuppliers([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    if (!form.name.trim()) {
      setError("Supplier name is required.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      await scope3Api.createSupplier({
        name: form.name.trim(),
        scope3_category: Number(form.category),
        emissions_kg: Number(form.emissions || 0),
        spend_usd: Number(form.spend || 0),
        pcf_received: form.pcf,
        dq_score: form.dq ? Number(form.dq) : null,
        supplier_sbt_status: form.sbt,
      });
      setShowForm(false);
      setForm({ name: "", category: "1", emissions: "", spend: "", pcf: false, dq: "", sbt: "none" });
      setCohort(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add supplier.");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await scope3Api.deleteSupplier(id);
      setCohort(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete supplier.");
    }
  };

  const handleCohort = async () => {
    if (hotspots.length === 0) {
      setError("Pick at least one hotspot category.");
      return;
    }
    setBuildingCohort(true);
    setError(null);
    try {
      setCohort(
        await scope3Api.supplierCohort({
          hotspot_categories: hotspots,
          top_n: Number(topN || 5),
          basis,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to build cohort.");
    } finally {
      setBuildingCohort(false);
    }
  };

  const toggleHotspot = (n: number) =>
    setHotspots((h) => (h.includes(n) ? h.filter((x) => x !== n) : [...h, n].sort((a, b) => a - b)));

  const cohortIds = new Set((cohort?.members ?? []).map((m) => m.supplier_id));
  const loading = suppliers === null && !error;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Supplier program</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Track suppliers, build a hotspot cohort for outreach, and watch program coverage.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      {/* Scorecard */}
      {scorecard && (
        <div className="mb-6 grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
          <Kpi label="Suppliers" value={String(scorecard.supplier_count)} />
          <Kpi label="PCF coverage" value={`${scorecard.pcf_coverage_pct.toFixed(0)}%`} />
          <Kpi label="Emissions covered" value={`${scorecard.emissions_covered_pct.toFixed(0)}%`} />
          <Kpi label="Avg data quality" value={scorecard.avg_dq != null ? `${scorecard.avg_dq.toFixed(1)}/5` : "—"} />
          <Kpi
            label="SBT status"
            value={`${scorecard.sbt_committed_count} / ${scorecard.sbt_validated_count}`}
            hint="committed / validated"
          />
        </div>
      )}

      {/* Cohort builder */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Build hotspot cohort</CardTitle>
          <CardDescription>Prioritize outreach to the top suppliers in your highest-emitting categories.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Hotspot categories</Label>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {ALL_CATEGORIES.map((n) => (
                <button
                  key={n}
                  type="button"
                  title={SCOPE3_CATEGORY_NAMES[n]}
                  onClick={() => toggleHotspot(n)}
                  className={`h-7 w-7 rounded-full border text-xs transition-colors ${
                    hotspots.includes(n) ? "border-primary bg-primary/10 text-foreground" : "border-border text-muted-foreground"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <Label htmlFor="basis">Basis</Label>
              <Select value={basis} onValueChange={setBasis}>
                <SelectTrigger id="basis" className="w-40"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="emissions">Emissions</SelectItem>
                  <SelectItem value="spend">Spend</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="topn">Top N</Label>
              <Input id="topn" type="number" className="w-24" value={topN} onChange={(e) => setTopN(e.target.value)} />
            </div>
            <Button onClick={handleCohort} disabled={buildingCohort}>
              {buildingCohort ? "Building..." : "Build cohort"}
            </Button>
            {cohort && (
              <span className="text-sm">
                Cohort covers{" "}
                <span className="font-mono font-semibold text-green-600">
                  {cohort.emissions_covered_pct.toFixed(0)}%
                </span>{" "}
                of emissions
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Supplier table */}
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-tight">Suppliers</h2>
        {!showForm && (
          <Button size="sm" onClick={() => setShowForm(true)}>
            <Plus className="mr-1 h-4 w-4" /> New supplier
          </Button>
        )}
      </div>

      {showForm && (
        <Card className="mb-4">
          <CardContent className="grid gap-3 py-4 sm:grid-cols-3">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input id="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="cat">Category</Label>
              <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                <SelectTrigger id="cat"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ALL_CATEGORIES.map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n} · {SCOPE3_CATEGORY_NAMES[n]}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="sbt">SBT status</Label>
              <Select value={form.sbt} onValueChange={(v) => setForm({ ...form, sbt: v })}>
                <SelectTrigger id="sbt"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SBT_STATUSES.map((s) => (
                    <SelectItem key={s} value={s} className="capitalize">{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="em">Emissions (kg CO₂e)</Label>
              <Input id="em" type="number" value={form.emissions} onChange={(e) => setForm({ ...form, emissions: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="sp">Spend (USD)</Label>
              <Input id="sp" type="number" value={form.spend} onChange={(e) => setForm({ ...form, spend: e.target.value })} />
            </div>
            <div>
              <Label htmlFor="dq">Data quality (0–5)</Label>
              <Input id="dq" type="number" value={form.dq} onChange={(e) => setForm({ ...form, dq: e.target.value })} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4" checked={form.pcf} onChange={(e) => setForm({ ...form, pcf: e.currentTarget.checked })} />
              PCF received
            </label>
            <div className="flex items-end justify-end gap-2 sm:col-span-2">
              <Button variant="outline" onClick={() => setShowForm(false)} disabled={creating}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? "Adding..." : "Add supplier"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Skeleton className="h-40 w-full rounded-lg" />
      ) : suppliers && suppliers.length > 0 ? (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-left">
                <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Supplier</th>
                <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Cat</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium uppercase text-muted-foreground">Emissions</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium uppercase text-muted-foreground">Spend</th>
                <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">PCF</th>
                <th className="px-4 py-2.5 text-right text-xs font-medium uppercase text-muted-foreground">DQ</th>
                <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">SBT</th>
                <th className="px-4 py-2.5"></th>
              </tr>
            </thead>
            <tbody>
              {suppliers.map((s) => (
                <tr
                  key={s.supplier_id}
                  className={`border-b border-border last:border-0 ${cohortIds.has(s.supplier_id) ? "bg-primary/5" : ""}`}
                >
                  <td className="px-4 py-2.5 font-medium">
                    {s.name}
                    {cohortIds.has(s.supplier_id) && (
                      <span className="text-primary ml-2 text-xs font-semibold uppercase">cohort</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">Cat {s.scope3_category}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{formatKg(s.emissions_kg)}</td>
                  <td className="px-4 py-2.5 text-right font-mono">${(s.spend_usd / 1_000_000).toFixed(1)}M</td>
                  <td className="px-4 py-2.5 font-mono">
                    {s.pcf_received ? <span className="text-green-600">✓</span> : <span className="text-muted-foreground">✗</span>}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono">{s.dq_score != null ? s.dq_score.toFixed(1) : "—"}</td>
                  <td className="px-4 py-2.5">
                    <Badge variant={sbtVariant(s.supplier_sbt_status)} className="capitalize">
                      {s.supplier_sbt_status}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      type="button"
                      onClick={() => handleDelete(s.supplier_id)}
                      className="text-muted-foreground hover:text-destructive"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="h-5 w-5" /> No suppliers yet
            </CardTitle>
            <CardDescription>Add your first supplier to start building the program.</CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
