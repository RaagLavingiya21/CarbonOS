"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ClipboardCheck } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  scope1Api,
  type S1OcrExtraction,
  type S1Source,
} from "@/lib/scope1-api";

const FUELS = ["natural_gas", "diesel_no2", "propane", "residual_oil_no6"];
const UNITS = ["therms", "mmBtu", "Ccf", "Mcf", "gal", "ton"];

function confidenceVariant(c: number): "low" | "medium" | "high" {
  if (c >= 0.85) return "low";      // green = trustworthy
  if (c >= 0.6) return "medium";    // amber
  return "high";                    // red = needs attention
}

function field(ext: S1OcrExtraction, name: string): string {
  return ext.extracted[name]?.value ?? "";
}

export default function Scope1ReviewPage() {
  const [queue, setQueue] = useState<S1OcrExtraction[]>([]);
  const [sources, setSources] = useState<S1Source[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [parsing, pending, approved, s] = await Promise.all([
        scope1Api.ocrQueue("parsing"),        // Bayou, awaiting parse
        scope1Api.ocrQueue("pending_review"), // Claude low-confidence
        scope1Api.ocrQueue("approved"),       // ready to map + apply
        scope1Api.listSources(),
      ]);
      setQueue([...parsing, ...pending, ...approved]);
      setSources(s);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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
          <ClipboardCheck className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-h1">Review queue</h1>
        </div>
        <p className="mt-2 text-small text-muted-foreground">
          Low-confidence OCR extractions from uploaded bills. Verify the fields, map to a source,
          and approve to create the record.
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {loading ? (
        <p className="text-small text-muted-foreground">Loading…</p>
      ) : queue.length === 0 ? (
        <Alert>
          <AlertDescription>
            Nothing to review. Upload a bill in{" "}
            <Link href="/scope-1/data" className="font-medium underline-offset-4 hover:underline">
              Add activity data
            </Link>
            .
          </AlertDescription>
        </Alert>
      ) : (
        queue.map((ext) =>
          ext.status === "parsing" ? (
            <ParsingCard key={ext.id} ext={ext} onDone={load} onError={setError} />
          ) : (
            <ReviewCard key={ext.id} ext={ext} sources={sources} onDone={load} onError={setError} />
          ),
        )
      )}
    </div>
  );
}

function ParsingCard({
  ext,
  onDone,
  onError,
}: {
  ext: S1OcrExtraction;
  onDone: () => void;
  onError: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setBusy(true);
    try {
      await scope1Api.ocrRefresh(ext.id);
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-h3">
          {ext.doc_kind.replace(/_/g, " ")}
          <Badge variant="info">Parsing at Bayou</Badge>
        </CardTitle>
        <CardDescription>Bayou is parsing this bill. Refresh to check if it&apos;s ready.</CardDescription>
      </CardHeader>
      <CardContent>
        <Button type="button" variant="outline" onClick={refresh} disabled={busy}>
          Refresh
        </Button>
      </CardContent>
    </Card>
  );
}

function ReviewCard({
  ext,
  sources,
  onDone,
  onError,
}: {
  ext: S1OcrExtraction;
  sources: S1Source[];
  onDone: () => void;
  onError: (message: string) => void;
}) {
  const [sourceId, setSourceId] = useState("");
  const [fuel, setFuel] = useState("natural_gas");
  const [amount, setAmount] = useState(field(ext, "consumption_quantity") || field(ext, "quantity"));
  const [unit, setUnit] = useState(field(ext, "consumption_unit") || field(ext, "unit") || "therms");
  const [periodStart, setPeriodStart] = useState(field(ext, "billing_period_start"));
  const [periodEnd, setPeriodEnd] = useState(field(ext, "billing_period_end"));
  const [busy, setBusy] = useState(false);

  async function approve() {
    if (!sourceId || !amount || !unit || !periodStart || !periodEnd) return;
    setBusy(true);
    try {
      await scope1Api.ocrReview(ext.id, {
        action: "approve",
        emission_source_id: sourceId,
        fuel_or_activity: fuel,
        activity_value: Number(amount),
        activity_unit: unit,
        period_start: periodStart,
        period_end: periodEnd,
      });
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    try {
      await scope1Api.ocrReview(ext.id, { action: "reject" });
      onDone();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const sourceOptions = sources.filter((s) => s.source_category === "stationary_combustion");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-h3">
          {ext.doc_kind.replace(/_/g, " ")}
          <Badge variant={confidenceVariant(ext.min_confidence ?? 0)}>
            min conf {((ext.min_confidence ?? 0) * 100).toFixed(0)}%
          </Badge>
        </CardTitle>
        <CardDescription>Extracted fields — check the amber/red ones.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {Object.entries(ext.extracted).map(([name, f]) =>
            f.value ? (
              <span
                key={name}
                className="inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-caption"
              >
                <span className="text-muted-foreground">{name.replace(/_/g, " ")}:</span>
                <span className="font-medium">{f.value}</span>
                <Badge variant={confidenceVariant(f.confidence)}>{(f.confidence * 100).toFixed(0)}%</Badge>
              </span>
            ) : null,
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Source</Label>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="h-9 w-full rounded-md border bg-card px-3 text-small"
            >
              <option value="">Select…</option>
              {sourceOptions.map((s) => (
                <option key={s.id} value={s.id}>{s.source_name}</option>
              ))}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Fuel</Label>
            <select value={fuel} onChange={(e) => setFuel(e.target.value)} className="h-9 w-full rounded-md border bg-card px-3 text-small">
              {FUELS.map((fl) => <option key={fl} value={fl}>{fl.replace(/_/g, " ")}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Amount</Label>
            <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Unit</Label>
            <select value={unit} onChange={(e) => setUnit(e.target.value)} className="h-9 w-full rounded-md border bg-card px-3 text-small">
              {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
          <div className="space-y-1.5">
            <Label>Period start</Label>
            <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Period end</Label>
            <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} />
          </div>
        </div>

        <div className="flex gap-2">
          <Button type="button" onClick={approve} disabled={busy || !sourceId || !amount || !periodStart || !periodEnd}>
            Approve &amp; create record
          </Button>
          <Button type="button" variant="outline" onClick={reject} disabled={busy}>
            Reject
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
