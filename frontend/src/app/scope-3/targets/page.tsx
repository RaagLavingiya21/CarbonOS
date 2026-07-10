"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Check, Target as TargetIcon } from "lucide-react";

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
  DraftTarget,
  InventoryVersion,
  Target,
  TargetWizardPayload,
  scope3Api,
  SCOPE3_CATEGORY_NAMES,
} from "@/lib/scope3-api";
import { formatKg } from "@/lib/utils";

const ALL_CATEGORIES = Array.from({ length: 15 }, (_, i) => i + 1);
const CURRENT_YEAR = new Date().getFullYear();

function TrajectoryChart({ points }: { points: { year: number; kg: number }[] }) {
  if (points.length < 2) return null;
  const w = 300;
  const h = 130;
  const padL = 8;
  const padR = 8;
  const padT = 10;
  const padB = 22;
  const years = points.map((p) => p.year);
  const kgs = points.map((p) => p.kg);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const maxKg = Math.max(...kgs);
  const minKg = Math.min(...kgs);
  const span = maxKg - minKg || 1;
  const x = (yr: number) =>
    padL + ((yr - minYear) / (maxYear - minYear || 1)) * (w - padL - padR);
  const y = (kg: number) =>
    padT + (1 - (kg - minKg) / span) * (h - padT - padB);
  const line = points.map((p) => `${x(p.year)},${y(p.kg)}`).join(" ");
  const area = `${x(points[0].year)},${h - padB} ${line} ${x(
    points[points.length - 1].year,
  )},${h - padB}`;

  return (
    <figure className="m-0 rounded-md border border-border bg-muted/40 p-2">
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img" aria-label="Emissions reduction trajectory">
        <line x1={padL} y1={h - padB} x2={w - padR} y2={h - padB} stroke="hsl(var(--border))" />
        <polygon points={area} fill="hsl(var(--primary))" opacity={0.08} />
        <polyline
          points={line}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          strokeLinejoin="round"
        />
        <circle cx={x(points[0].year)} cy={y(points[0].kg)} r={3} fill="hsl(var(--primary))" />
        <circle
          cx={x(points[points.length - 1].year)}
          cy={y(points[points.length - 1].kg)}
          r={3}
          className="fill-green-600"
        />
      </svg>
      <figcaption className="mt-1 flex justify-between text-xs text-muted-foreground">
        <span>{minYear}</span>
        <span>{maxYear}</span>
      </figcaption>
    </figure>
  );
}

export default function TargetsPage() {
  const [inventories, setInventories] = useState<InventoryVersion[]>([]);
  const [targets, setTargets] = useState<Target[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<DraftTarget | null>(null);
  const [covered, setCovered] = useState<number[]>(ALL_CATEGORIES);

  const [form, setForm] = useState({
    inventoryId: "",
    baseYear: CURRENT_YEAR - 2,
    targetYear: CURRENT_YEAR + 6,
    reductionPct: 42,
    method: "absolute",
    horizon: "near_term",
    sector: "",
  });

  const load = async () => {
    try {
      const [invs, tgts] = await Promise.all([
        scope3Api.listInventories().catch(() => [] as InventoryVersion[]),
        scope3Api.listTargets(),
      ]);
      setInventories(invs);
      setTargets(tgts);
      setForm((f) => ({
        ...f,
        inventoryId: f.inventoryId || (invs[0] ? String(invs[0].inventory_id) : ""),
      }));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load targets.");
      setTargets([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const payload = (): TargetWizardPayload => ({
    inventory_id: Number(form.inventoryId),
    base_year: Number(form.baseYear),
    target_year: Number(form.targetYear),
    reduction_pct: Number(form.reductionPct),
    method: form.method,
    horizon: form.horizon,
    version: "v2.0",
    covered_categories: covered,
    sector: form.sector.trim(),
    flag_kg_co2e: 0,
  });

  const handlePreview = async () => {
    if (!form.inventoryId) {
      setError("Select an inventory first.");
      return;
    }
    setPreviewing(true);
    setError(null);
    try {
      setDraft(await scope3Api.targetWizard(payload()));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to preview target.");
    } finally {
      setPreviewing(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await scope3Api.createTarget(payload());
      setDraft(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save target.");
    } finally {
      setSaving(false);
    }
  };

  const toggleCat = (n: number) =>
    setCovered((c) => (c.includes(n) ? c.filter((x) => x !== n) : [...c, n].sort((a, b) => a - b)));

  const chartPoints = useMemo(
    () => (draft ? draft.trajectory.map((t) => ({ year: t.year, kg: t.target_kg_co2e })) : []),
    [draft],
  );

  const loading = targets === null && !error;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Science-based targets</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Set an SBTi-conformant Scope 3 reduction target — the draft updates when you
            preview.
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
            <CardDescription>SBTi v2.0</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="inventory">Inventory (base)</Label>
              <Select
                value={form.inventoryId}
                onValueChange={(v) => setForm({ ...form, inventoryId: v })}
              >
                <SelectTrigger id="inventory">
                  <SelectValue placeholder="Select an inventory" />
                </SelectTrigger>
                <SelectContent>
                  {inventories.map((inv) => (
                    <SelectItem key={inv.inventory_id} value={String(inv.inventory_id)}>
                      {inv.reporting_year} · {inv.status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="base-year">Base year</Label>
                <Input
                  id="base-year"
                  type="number"
                  value={form.baseYear}
                  onChange={(e) => setForm({ ...form, baseYear: Number(e.target.value) })}
                />
              </div>
              <div>
                <Label htmlFor="target-year">Target year</Label>
                <Input
                  id="target-year"
                  type="number"
                  value={form.targetYear}
                  onChange={(e) => setForm({ ...form, targetYear: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="reduction">Reduction %</Label>
                <Input
                  id="reduction"
                  type="number"
                  value={form.reductionPct}
                  onChange={(e) => setForm({ ...form, reductionPct: Number(e.target.value) })}
                />
              </div>
              <div>
                <Label htmlFor="method">Method</Label>
                <Select value={form.method} onValueChange={(v) => setForm({ ...form, method: v })}>
                  <SelectTrigger id="method">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="absolute">Absolute</SelectItem>
                    <SelectItem value="intensity">Intensity</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="horizon">Horizon</Label>
                <Select value={form.horizon} onValueChange={(v) => setForm({ ...form, horizon: v })}>
                  <SelectTrigger id="horizon">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="near_term">Near-term</SelectItem>
                    <SelectItem value="net_zero">Net-zero</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="sector">Sector</Label>
                <Input
                  id="sector"
                  placeholder="optional"
                  value={form.sector}
                  onChange={(e) => setForm({ ...form, sector: e.target.value })}
                />
              </div>
            </div>
            <div>
              <Label>Covered Scope 3 categories</Label>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {ALL_CATEGORIES.map((n) => (
                  <button
                    key={n}
                    type="button"
                    title={SCOPE3_CATEGORY_NAMES[n]}
                    onClick={() => toggleCat(n)}
                    className={`h-7 w-7 rounded-full border text-xs transition-colors ${
                      covered.includes(n)
                        ? "border-primary bg-primary/10 text-foreground"
                        : "border-border text-muted-foreground"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
            <Button onClick={handlePreview} disabled={previewing} className="w-full">
              {previewing ? "Previewing..." : "Preview draft target"}
            </Button>
          </CardContent>
        </Card>

        {/* Preview */}
        <Card className="bg-muted/30">
          <CardHeader>
            <CardTitle className="text-base">Draft target</CardTitle>
            <CardDescription>
              {draft ? `${draft.version} · ${draft.category_class}` : "Preview to see the draft"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!draft ? (
              <p className="text-muted-foreground text-sm">
                Fill in the inputs and press <b>Preview draft target</b>.
              </p>
            ) : (
              <>
                <div className="flex items-center gap-4">
                  <div>
                    <p className="font-mono text-2xl font-semibold">
                      {formatKg(draft.total_scope3_kg)}
                    </p>
                    <p className="text-muted-foreground text-xs">{form.baseYear} base</p>
                  </div>
                  <span className="text-muted-foreground">→</span>
                  <div>
                    <p className="font-mono text-2xl font-semibold text-green-600">
                      {formatKg(draft.total_scope3_kg * (1 - Number(form.reductionPct) / 100))}
                    </p>
                    <p className="text-muted-foreground text-xs">{form.targetYear} target</p>
                  </div>
                </div>

                <TrajectoryChart points={chartPoints} />

                <div
                  className={`flex items-start gap-2 rounded-md border p-3 text-sm ${
                    draft.ambition.meets_reference
                      ? "border-green-600/30 bg-green-600/5"
                      : "border-data-medium/40 bg-data-medium-bg"
                  }`}
                >
                  {draft.ambition.meets_reference && (
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
                  )}
                  <div>
                    <p className="font-medium">
                      {draft.ambition.meets_reference ? "Meets reference" : "Below reference"} —{" "}
                      {draft.ambition.chosen_reduction_pct}% vs{" "}
                      {draft.ambition.reference_reduction_pct}%
                    </p>
                    <p className="text-muted-foreground">{draft.ambition.note}</p>
                  </div>
                </div>

                <div className="space-y-1.5 text-sm">
                  <div className="flex justify-between border-b border-border py-1">
                    <span className="text-muted-foreground">Scope 3 target</span>
                    <span>{draft.scope3_target_mandatory ? "Mandatory" : "Optional"}</span>
                  </div>
                  <div className="flex justify-between border-b border-border py-1">
                    <span className="text-muted-foreground">Base-year assurance</span>
                    <span className={draft.base_year_assurance_required ? "text-data-medium" : ""}>
                      {draft.base_year_assurance_required ? "Required" : "Not required"}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-border py-1">
                    <span className="text-muted-foreground">FLAG target</span>
                    <span className={draft.flag?.is_flag_required ? "text-data-medium" : "text-green-600"}>
                      {draft.flag?.is_flag_required ? "Required" : "Not required"}
                    </span>
                  </div>
                </div>

                {draft.coverage_gap.length > 0 && (
                  <div>
                    <p className="text-muted-foreground text-xs font-medium uppercase">
                      Coverage gap
                    </p>
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      {draft.coverage_gap.map((n) => (
                        <Badge key={n} variant="medium">
                          Cat {n} · {SCOPE3_CATEGORY_NAMES[n]}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {draft.notes.map((n, i) => (
                  <p
                    key={i}
                    className="rounded-md border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground"
                  >
                    {n}
                  </p>
                ))}

                <Button onClick={handleSave} disabled={saving} className="w-full">
                  {saving ? "Saving..." : "Save draft target"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Saved targets */}
      <div className="mt-8">
        <h2 className="mb-3 text-sm font-semibold tracking-tight">Saved targets</h2>
        {loading ? (
          <Skeleton className="h-24 w-full rounded-lg" />
        ) : targets && targets.length > 0 ? (
          <div className="space-y-2">
            {targets.map((t) => (
              <Card key={t.target_id}>
                <CardContent className="flex items-center justify-between py-3 text-sm">
                  <div>
                    <p className="font-medium capitalize">
                      {t.type.replace(/_/g, " ")} · {t.method}
                    </p>
                    <p className="text-muted-foreground font-mono text-xs">
                      {t.base_year}→{t.target_year} · −{t.reduction_pct}% · {t.sbti_version}
                    </p>
                  </div>
                  <Badge variant={t.status === "validated" ? "high" : "neutral"} className="capitalize">
                    {t.status}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <TargetIcon className="h-5 w-5" /> No targets yet
              </CardTitle>
              <CardDescription>Preview and save a draft to get started.</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </div>
  );
}
