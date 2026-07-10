"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowLeft, CheckCircle2, HelpCircle, XCircle } from "lucide-react";

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
  CompanyProfile,
  Obligation,
  ObligationEvaluation,
  scope3Api,
} from "@/lib/scope3-api";

const EMPTY_PROFILE: CompanyProfile = {
  annual_revenue_usd: null,
  employee_count: null,
  is_us_entity: false,
  does_business_in_ca: false,
  eu_turnover_eur: null,
  eu_subsidiary: false,
  eu_branch_turnover_eur: null,
  listed_jurisdictions: [],
  sector: "",
  is_flag_sector: false,
  key_customers: [],
};

function toNum(v: string): number | null {
  const t = v.trim();
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function toList(v: string): string[] {
  return v
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function CheckField({
  id,
  label,
  checked,
  onChange,
}: {
  id: string;
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label htmlFor={id} className="flex items-center gap-2 text-sm">
      <input
        id={id}
        type="checkbox"
        className="h-4 w-4 rounded border-input"
        checked={checked}
        onChange={(e) => onChange(e.currentTarget.checked)}
      />
      {label}
    </label>
  );
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const variant =
    confidence === "high" || confidence === "medium" || confidence === "low"
      ? confidence
      : "neutral";
  return (
    <Badge variant={variant} className="capitalize">
      {confidence || "—"} confidence
    </Badge>
  );
}

function ObligationCard({ o }: { o: Obligation }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-base">{o.framework}</CardTitle>
            <CardDescription>{o.threshold_detail}</CardDescription>
          </div>
          <ConfidenceBadge confidence={o.confidence} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <p>{o.reason}</p>
        {o.due.length > 0 && (
          <div>
            <p className="text-muted-foreground text-xs font-medium uppercase">Due</p>
            <ul className="mt-1 space-y-1">
              {o.due.map((d, i) => (
                <li key={i}>
                  <span className="font-medium">{d.what}</span>
                  {d.date ? ` — ${d.date}` : ""}
                  {d.note ? ` (${d.note})` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
        {o.assurance && (
          <p>
            <span className="text-muted-foreground text-xs font-medium uppercase">
              Assurance:{" "}
            </span>
            {o.assurance}
          </p>
        )}
        {o.citation && (
          <p className="text-muted-foreground text-xs">{o.citation}</p>
        )}
      </CardContent>
    </Card>
  );
}

function Group({
  title,
  icon: Icon,
  items,
}: {
  title: string;
  icon: typeof CheckCircle2;
  items: Obligation[];
}) {
  if (items.length === 0) return null;
  return (
    <section className="space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
        <Icon className="h-4 w-4" /> {title}
        <span className="text-muted-foreground font-normal">({items.length})</span>
      </h3>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((o) => (
          <ObligationCard key={o.rule_id} o={o} />
        ))}
      </div>
    </section>
  );
}

export default function ObligationsPage() {
  const [form, setForm] = useState<CompanyProfile>(EMPTY_PROFILE);
  const [jurisdictionsText, setJurisdictionsText] = useState("");
  const [customersText, setCustomersText] = useState("");
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [saving, setSaving] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [result, setResult] = useState<ObligationEvaluation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    scope3Api
      .getCompanyProfile()
      .then((p) => {
        if (p) {
          setForm({ ...EMPTY_PROFILE, ...p });
          setJurisdictionsText((p.listed_jurisdictions ?? []).join(", "));
          setCustomersText((p.key_customers ?? []).join(", "));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile."))
      .finally(() => setLoadingProfile(false));
  }, []);

  const buildPayload = (): CompanyProfile => ({
    ...form,
    listed_jurisdictions: toList(jurisdictionsText),
    key_customers: toList(customersText),
  });

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const saved = await scope3Api.saveCompanyProfile(buildPayload());
      setForm({ ...EMPTY_PROFILE, ...saved });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile.");
    } finally {
      setSaving(false);
    }
  };

  const handleEvaluate = async () => {
    setEvaluating(true);
    setError(null);
    try {
      await scope3Api.saveCompanyProfile(buildPayload());
      const res = await scope3Api.evaluateObligations();
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to evaluate obligations.");
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Obligations — is this my problem?
          </h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Tell us about the company, then evaluate which disclosure regimes apply.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      {loadingProfile ? (
        <Skeleton className="h-[420px] w-full rounded-lg" />
      ) : (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>Company profile</CardTitle>
            <CardDescription>
              Leave a field blank if unknown — unknowns are treated as uncertain, never
              as a free pass.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="revenue">Annual revenue (USD)</Label>
                <Input
                  id="revenue"
                  type="number"
                  value={form.annual_revenue_usd ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, annual_revenue_usd: toNum(e.target.value) })
                  }
                />
              </div>
              <div>
                <Label htmlFor="employees">Employee count</Label>
                <Input
                  id="employees"
                  type="number"
                  value={form.employee_count ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, employee_count: toNum(e.target.value) })
                  }
                />
              </div>
              <div>
                <Label htmlFor="eu-turnover">EU turnover (EUR)</Label>
                <Input
                  id="eu-turnover"
                  type="number"
                  value={form.eu_turnover_eur ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, eu_turnover_eur: toNum(e.target.value) })
                  }
                />
              </div>
              <div>
                <Label htmlFor="eu-branch">EU branch turnover (EUR)</Label>
                <Input
                  id="eu-branch"
                  type="number"
                  value={form.eu_branch_turnover_eur ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, eu_branch_turnover_eur: toNum(e.target.value) })
                  }
                />
              </div>
              <div>
                <Label htmlFor="sector">Sector</Label>
                <Input
                  id="sector"
                  value={form.sector}
                  onChange={(e) => setForm({ ...form, sector: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="jurisdictions">Listed jurisdictions</Label>
                <Input
                  id="jurisdictions"
                  placeholder="US, EU, UK"
                  value={jurisdictionsText}
                  onChange={(e) => setJurisdictionsText(e.target.value)}
                />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="customers">Key customers</Label>
                <Input
                  id="customers"
                  placeholder="Comma-separated (used for cascade exposure)"
                  value={customersText}
                  onChange={(e) => setCustomersText(e.target.value)}
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <CheckField
                id="us-entity"
                label="US entity"
                checked={form.is_us_entity}
                onChange={(v) => setForm({ ...form, is_us_entity: v })}
              />
              <CheckField
                id="ca-business"
                label="Does business in California"
                checked={form.does_business_in_ca}
                onChange={(v) => setForm({ ...form, does_business_in_ca: v })}
              />
              <CheckField
                id="eu-sub"
                label="Has EU subsidiary"
                checked={form.eu_subsidiary}
                onChange={(v) => setForm({ ...form, eu_subsidiary: v })}
              />
              <CheckField
                id="flag-sector"
                label="FLAG sector (forest/land/agriculture)"
                checked={form.is_flag_sector}
                onChange={(v) => setForm({ ...form, is_flag_sector: v })}
              />
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={handleSave} disabled={saving || evaluating}>
                {saving ? "Saving..." : "Save profile"}
              </Button>
              <Button onClick={handleEvaluate} disabled={saving || evaluating}>
                {evaluating ? "Evaluating..." : "Evaluate obligations"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {result && (
        <div className="space-y-8">
          <Card>
            <CardHeader>
              <CardTitle>{result.business_case.headline}</CardTitle>
              <CardDescription>
                Ruleset {result.ruleset_version} · {result.business_case.applicable_count}{" "}
                applicable · {result.business_case.uncertain_count} uncertain
              </CardDescription>
            </CardHeader>
            {(result.business_case.at_stake.length > 0 ||
              result.business_case.watch_items.length > 0) && (
              <CardContent className="grid gap-4 text-sm sm:grid-cols-2">
                {result.business_case.at_stake.length > 0 && (
                  <div>
                    <p className="text-muted-foreground text-xs font-medium uppercase">
                      At stake
                    </p>
                    <ul className="mt-1 list-disc pl-4">
                      {result.business_case.at_stake.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {result.business_case.watch_items.length > 0 && (
                  <div>
                    <p className="text-muted-foreground text-xs font-medium uppercase">
                      Watch items
                    </p>
                    <ul className="mt-1 list-disc pl-4">
                      {result.business_case.watch_items.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            )}
          </Card>

          <Group title="Applicable" icon={CheckCircle2} items={result.applicable} />
          <Group title="Uncertain" icon={HelpCircle} items={result.uncertain} />
          <Group title="Not applicable" icon={XCircle} items={result.not_applicable} />

          {result.cascade.length > 0 && (
            <section className="space-y-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
                <AlertTriangle className="h-4 w-4" /> Customer cascade exposure
              </h3>
              <div className="grid gap-3 md:grid-cols-2">
                {result.cascade.map((c, i) => (
                  <Card key={i}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">{c.customer}</CardTitle>
                      <CardDescription>
                        Matches {c.matched_buyer} · {c.regimes.join(", ")}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="text-sm">{c.rationale}</CardContent>
                  </Card>
                ))}
              </div>
            </section>
          )}

          {result.timeline.length > 0 && (
            <section className="space-y-3">
              <h3 className="text-sm font-semibold tracking-tight">Compliance timeline</h3>
              <Card>
                <CardContent className="divide-y p-0">
                  {result.timeline.map((t, i) => (
                    <div key={i} className="flex items-center gap-4 px-6 py-3 text-sm">
                      <span className="font-mono w-28 shrink-0">{t.date}</span>
                      <span className="w-32 shrink-0 font-medium">{t.framework}</span>
                      <span className="text-muted-foreground">{t.what}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
