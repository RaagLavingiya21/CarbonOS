"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";

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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ClaimAssessment,
  Lever,
  MacPoint,
  scope3Api,
  SCOPE3_CATEGORY_NAMES,
} from "@/lib/scope3-api";

const ALL_CATEGORIES = Array.from({ length: 15 }, (_, i) => i + 1);
const TABS = [
  { id: "levers", label: "Levers" },
  { id: "mac", label: "MAC curve" },
  { id: "claims", label: "Claims check" },
] as const;
type TabId = (typeof TABS)[number]["id"];

function verdictVariant(verdict: string) {
  const v = verdict.toLowerCase();
  if (v.includes("fail") || v.includes("prohibit")) return "low" as const;
  if (v.includes("risk") || v.includes("warn")) return "medium" as const;
  if (v.includes("pass") || v.includes("ok")) return "high" as const;
  return "neutral" as const;
}

function MacChart({ points }: { points: MacPoint[] }) {
  if (points.length === 0) return null;
  const w = 620;
  const h = 280;
  const padL = 46;
  const padR = 16;
  const padT = 16;
  const padB = 40;
  const xMax = Math.max(...points.map((p) => p.cumulative_abatement_tco2e), 1);
  const costs = points.map((p) => p.cost_per_tco2e);
  const yMax = Math.max(0, ...costs) * 1.1 || 1;
  const yMin = Math.min(0, ...costs) * 1.1;
  const span = yMax - yMin || 1;
  const xs = (v: number) => padL + (v / xMax) * (w - padL - padR);
  const ys = (v: number) => padT + ((yMax - v) / span) * (h - padT - padB);
  const zeroY = ys(0);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Marginal abatement cost curve">
      <line x1={padL} y1={padT} x2={padL} y2={h - padB} stroke="hsl(var(--muted-foreground))" strokeWidth={1} />
      <line x1={padL} y1={h - padB} x2={w - padR} y2={h - padB} stroke="hsl(var(--muted-foreground))" strokeWidth={1} />
      <line x1={padL} y1={zeroY} x2={w - padR} y2={zeroY} stroke="hsl(var(--border))" strokeWidth={1.5} strokeDasharray="4 3" />
      <text x={w - padR} y={zeroY - 4} textAnchor="end" fontFamily="var(--font-mono)" fontSize={10} fill="hsl(var(--muted-foreground))">
        $0 breakeven
      </text>
      {points.map((p) => {
        const xEnd = xs(p.cumulative_abatement_tco2e);
        const xStart = xs(p.cumulative_abatement_tco2e - p.abatement_tco2e);
        const saving = p.cost_per_tco2e < 0;
        const top = saving ? zeroY : ys(p.cost_per_tco2e);
        const height = Math.abs(ys(p.cost_per_tco2e) - zeroY);
        return (
          <rect
            key={p.lever_id}
            x={xStart}
            y={top}
            width={Math.max(1, xEnd - xStart - 1)}
            height={Math.max(1, height)}
            fill={saving ? "#16a34a" : "hsl(var(--primary))"}
            opacity={0.85}
          >
            <title>{`${p.name}: ${p.abatement_tco2e.toFixed(0)} tCO₂e @ $${p.cost_per_tco2e}/t`}</title>
          </rect>
        );
      })}
      <text x={(w + padL) / 2} y={h - 6} textAnchor="middle" fontSize={10} fill="hsl(var(--muted-foreground))">
        Cumulative abatement (tCO₂e)
      </text>
    </svg>
  );
}

export default function LeversPage() {
  const [tab, setTab] = useState<TabId>("levers");
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<number[]>([1, 4, 12]);

  const [levers, setLevers] = useState<Lever[] | null>(null);
  const [loadingLevers, setLoadingLevers] = useState(false);

  const [totals, setTotals] = useState<Record<string, string>>({});
  const [macPoints, setMacPoints] = useState<MacPoint[] | null>(null);
  const [buildingMac, setBuildingMac] = useState(false);

  const [claim, setClaim] = useState({
    text: "",
    primaryPct: "0",
    assured: false,
    jurisdiction: "EU",
    offset: false,
  });
  const [assessment, setAssessment] = useState<ClaimAssessment | null>(null);
  const [assessing, setAssessing] = useState(false);

  const toggleCat = (n: number) =>
    setCategories((c) => (c.includes(n) ? c.filter((x) => x !== n) : [...c, n].sort((a, b) => a - b)));

  const handleLoadLevers = async () => {
    if (categories.length === 0) {
      setError("Pick at least one category.");
      return;
    }
    setLoadingLevers(true);
    setError(null);
    try {
      setLevers(await scope3Api.listLevers(categories));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load levers.");
    } finally {
      setLoadingLevers(false);
    }
  };

  const handleBuildMac = async () => {
    const totalsNum: Record<string, number> = {};
    categories.forEach((c) => {
      const v = Number(totals[String(c)] || 0);
      if (v > 0) totalsNum[String(c)] = v;
    });
    if (Object.keys(totalsNum).length === 0) {
      setError("Enter a tCO₂e total for at least one category.");
      return;
    }
    setBuildingMac(true);
    setError(null);
    try {
      setMacPoints(await scope3Api.buildMac(totalsNum));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to build MAC curve.");
    } finally {
      setBuildingMac(false);
    }
  };

  const handleAssess = async () => {
    if (!claim.text.trim()) {
      setError("Enter a claim to assess.");
      return;
    }
    setAssessing(true);
    setError(null);
    try {
      setAssessment(
        await scope3Api.assessClaim({
          claim_text: claim.text.trim(),
          primary_data_share: Number(claim.primaryPct || 0) / 100,
          assured: claim.assured,
          jurisdiction: claim.jurisdiction,
          offset_based: claim.offset,
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to assess claim.");
    } finally {
      setAssessing(false);
    }
  };

  const CategoryToggles = () => (
    <div className="flex flex-wrap gap-1.5">
      {ALL_CATEGORIES.map((n) => (
        <button
          key={n}
          type="button"
          title={SCOPE3_CATEGORY_NAMES[n]}
          onClick={() => toggleCat(n)}
          className={`h-7 w-7 rounded-full border text-xs transition-colors ${
            categories.includes(n) ? "border-primary bg-primary/10 text-foreground" : "border-border text-muted-foreground"
          }`}
        >
          {n}
        </button>
      ))}
    </div>
  );

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Decarbonization &amp; claims</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Browse abatement levers, build a MAC curve, and check green claims for compliance.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-1 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm transition-colors ${
              tab === t.id
                ? "border-primary font-semibold text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      {tab === "levers" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Lever library</CardTitle>
              <CardDescription>Select the Scope 3 categories you want levers for.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <CategoryToggles />
              <Button onClick={handleLoadLevers} disabled={loadingLevers}>
                {loadingLevers ? "Loading..." : "Load levers"}
              </Button>
            </CardContent>
          </Card>

          {levers && (
            <Card className="overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-left">
                    <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Lever</th>
                    <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Cat</th>
                    <th className="px-4 py-2.5 text-right text-xs font-medium uppercase text-muted-foreground">Abatement</th>
                    <th className="px-4 py-2.5 text-right text-xs font-medium uppercase text-muted-foreground">$/tCO₂e</th>
                    <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {levers.map((l) => (
                    <tr key={l.lever_id} className="border-b border-border last:border-0">
                      <td className="px-4 py-2.5 font-medium">{l.name}</td>
                      <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">Cat {l.category}</td>
                      <td className="px-4 py-2.5 text-right font-mono">{l.abatement_pct}%</td>
                      <td className={`px-4 py-2.5 text-right font-mono ${l.cost_per_tco2e < 0 ? "text-green-600" : ""}`}>
                        {l.cost_per_tco2e < 0 ? "-" : ""}${Math.abs(l.cost_per_tco2e)}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-muted-foreground">{l.source || "—"}</td>
                    </tr>
                  ))}
                  {levers.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-muted-foreground px-4 py-6 text-center text-sm">
                        No levers matched those categories.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </Card>
          )}
        </div>
      )}

      {tab === "mac" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Category totals</CardTitle>
              <CardDescription>Enter your emissions (tCO₂e) per category, then build the curve.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <CategoryToggles />
              {categories.length > 0 && (
                <div className="grid gap-3 sm:grid-cols-3">
                  {categories.map((c) => (
                    <div key={c}>
                      <Label htmlFor={`tot-${c}`}>Cat {c} (tCO₂e)</Label>
                      <Input
                        id={`tot-${c}`}
                        type="number"
                        value={totals[String(c)] ?? ""}
                        onChange={(e) => setTotals({ ...totals, [String(c)]: e.target.value })}
                      />
                    </div>
                  ))}
                </div>
              )}
              <Button onClick={handleBuildMac} disabled={buildingMac}>
                {buildingMac ? "Building..." : "Build MAC curve"}
              </Button>
            </CardContent>
          </Card>

          {macPoints && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Marginal abatement cost curve</CardTitle>
                <CardDescription>Ranked cheapest-first · width = abatement, height = $/tCO₂e</CardDescription>
              </CardHeader>
              <CardContent>
                <MacChart points={macPoints} />
                <div className="mt-4 space-y-1">
                  {macPoints.map((p, i) => (
                    <div key={p.lever_id} className="flex items-center gap-3 border-b border-border py-1.5 text-sm last:border-0">
                      <span className="text-muted-foreground w-4 font-mono text-xs">{i + 1}</span>
                      <span className="flex-1">{p.name}</span>
                      <span className="text-muted-foreground font-mono text-xs">{p.abatement_tco2e.toFixed(0)} t</span>
                      <span className={`w-16 text-right font-mono ${p.cost_per_tco2e < 0 ? "text-green-600" : ""}`}>
                        {p.cost_per_tco2e < 0 ? "-" : ""}${Math.abs(p.cost_per_tco2e)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {tab === "claims" && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Assess a green claim</CardTitle>
              <CardDescription>Check a marketing claim for substantiation and compliance flags.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="claim">Claim text</Label>
                <Textarea
                  id="claim"
                  placeholder="e.g. Our product is carbon neutral"
                  value={claim.text}
                  onChange={(e) => setClaim({ ...claim, text: e.target.value })}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                <div>
                  <Label htmlFor="pd">Primary data (%)</Label>
                  <Input id="pd" type="number" value={claim.primaryPct} onChange={(e) => setClaim({ ...claim, primaryPct: e.target.value })} />
                </div>
                <div>
                  <Label htmlFor="jur">Jurisdiction</Label>
                  <Select value={claim.jurisdiction} onValueChange={(v) => setClaim({ ...claim, jurisdiction: v })}>
                    <SelectTrigger id="jur"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="EU">EU</SelectItem>
                      <SelectItem value="US">US</SelectItem>
                      <SelectItem value="UK">UK</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex flex-wrap gap-4">
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="h-4 w-4" checked={claim.assured} onChange={(e) => setClaim({ ...claim, assured: e.currentTarget.checked })} />
                  Third-party assured
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="h-4 w-4" checked={claim.offset} onChange={(e) => setClaim({ ...claim, offset: e.currentTarget.checked })} />
                  Offset-based
                </label>
              </div>
              <Button onClick={handleAssess} disabled={assessing}>
                {assessing ? "Assessing..." : "Assess claim"}
              </Button>
              <p className="text-muted-foreground border-t border-border pt-3 text-xs">
                Not legal advice · requires legal review before publishing.
              </p>
            </CardContent>
          </Card>

          {assessment && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base">Assessment</CardTitle>
                  <Badge variant={assessment.substantiable ? "high" : "low"}>
                    {assessment.substantiable ? "Substantiable" : "Not substantiable"}
                  </Badge>
                </div>
                <CardDescription>
                  {assessment.jurisdiction} · ruleset {assessment.ruleset_version}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm">{assessment.substantiation_reason}</p>
                {assessment.flags.map((f, i) => (
                  <div key={i} className="rounded-md border border-border p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{f.framework}</span>
                      <Badge variant={verdictVariant(f.verdict)}>{f.verdict}</Badge>
                    </div>
                    <p className="text-muted-foreground mt-1 text-xs">{f.note}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
