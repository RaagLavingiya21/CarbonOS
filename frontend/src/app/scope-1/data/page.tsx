"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  scope1Api,
  type S1CsvResult,
  type S1Evidence,
  type S1OcrExtraction,
  type S1Record,
  type S1Source,
  type S1Trace,
} from "@/lib/scope1-api";

import { InventoryPicker, fmtT, useInventories } from "../_lib";

const STATIONARY_UNITS = ["therms", "mmBtu", "GJ", "scf", "Ccf", "Mcf", "gal", "ton"];
const STATIONARY_FUELS = ["natural_gas", "diesel_no2", "propane", "residual_oil_no6"];
const MOBILE_FUELS = ["motor_gasoline", "diesel", "lpg", "cng", "lng"];

function labelFor(value: string): string {
  return value.replace(/_/g, " ");
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

function Selectable({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  placeholder?: string;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 w-full rounded-md border bg-card px-3 text-small"
    >
      <option value="">{placeholder ?? "Select…"}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

function ResultPanel({ record, onTrace }: { record: S1Record; onTrace: () => void }) {
  return (
    <Alert>
      <AlertDescription>
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="low">Recorded</Badge>
          <span className="text-small tabular-nums">
            CO₂ {fmtT(record.kg_co2_fossil)} kg · CH₄ {fmtT(record.kg_ch4)} kg · N₂O{" "}
            {fmtT(record.kg_n2o)} kg
          </span>
          {record.ef_source ? (
            <span className="text-caption text-muted-foreground">{record.ef_source}</span>
          ) : null}
          <Button type="button" variant="outline" size="sm" onClick={onTrace}>
            View source
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}

function TracePanel({ trace }: { trace: S1Trace }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>View source · {trace.ar_version}</CardTitle>
        <CardDescription>Every number traces to activity × emission factor × GWP.</CardDescription>
      </CardHeader>
      <CardContent>
        <table className="w-full text-left text-sm">
          <thead className="text-muted-foreground">
            <tr>
              <th className="py-1">Gas</th>
              <th className="py-1 text-right">kg</th>
              <th className="py-1 text-right">GWP-100</th>
              <th className="py-1 text-right">tCO₂e</th>
            </tr>
          </thead>
          <tbody>
            {trace.gases.map((gas) => (
              <tr key={gas.gas} className="border-t">
                <td className="py-1">{gas.gas}</td>
                <td className="py-1 text-right tabular-nums">{fmtT(gas.kg)}</td>
                <td className="py-1 text-right tabular-nums">{gas.gwp_100}</td>
                <td className="py-1 text-right tabular-nums">{fmtT(gas.tco2e)}</td>
              </tr>
            ))}
            <tr className="border-t font-medium">
              <td className="py-1">Total (× multiplier {trace.consolidation_multiplier})</td>
              <td />
              <td />
              <td className="py-1 text-right tabular-nums">{fmtT(trace.total_tco2e)}</td>
            </tr>
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

export default function Scope1DataPage() {
  const { inventories, activeId, setActiveId } = useInventories();
  const [sources, setSources] = useState<S1Source[]>([]);
  const [mode, setMode] = useState<"stationary" | "mobile">("stationary");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<S1Record | null>(null);
  const [trace, setTrace] = useState<S1Trace | null>(null);

  useEffect(() => {
    scope1Api.listSources().then(setSources).catch((err) => setError((err as Error).message));
  }, []);

  const showTrace = useCallback(async () => {
    if (!result) return;
    try {
      setTrace(await scope1Api.recordTrace(result.id));
    } catch (err) {
      setError((err as Error).message);
    }
  }, [result]);

  const sourceOptions = sources
    .filter((s) => s.source_category === `${mode}_combustion`)
    .map((s) => ({ value: s.id, label: s.source_name }));

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
          <h1 className="text-h1">Add activity data</h1>
          <p className="mt-2 text-small text-muted-foreground">
            Enter fuel or fleet consumption. The engine computes per-gas masses on save.
          </p>
        </div>
        <InventoryPicker inventories={inventories} activeId={activeId} onChange={setActiveId} />
      </div>

      <div className="inline-flex rounded-md border p-0.5">
        {(["stationary", "mobile"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => {
              setMode(option);
              setResult(null);
              setTrace(null);
            }}
            className={`rounded px-3 py-1 text-small ${
              mode === option ? "bg-primary text-primary-foreground" : "text-muted-foreground"
            }`}
          >
            {option === "stationary" ? "Stationary" : "Mobile / fleet"}
          </button>
        ))}
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {!activeId ? (
        <Alert>
          <AlertDescription>
            Create an inventory first in{" "}
            <Link href="/scope-1/setup" className="font-medium underline-offset-4 hover:underline">
              Set up inventory
            </Link>
            .
          </AlertDescription>
        </Alert>
      ) : mode === "stationary" ? (
        <StationaryForm
          inventoryId={activeId}
          sourceOptions={sourceOptions}
          onError={setError}
          onResult={(r) => {
            setResult(r);
            setTrace(null);
          }}
        />
      ) : (
        <MobileForm
          inventoryId={activeId}
          sourceOptions={sourceOptions}
          onError={setError}
          onResult={(r) => {
            setResult(r);
            setTrace(null);
          }}
        />
      )}

      {result ? <ResultPanel record={result} onTrace={showTrace} /> : null}
      {trace ? <TracePanel trace={trace} /> : null}

      {activeId ? <OcrUploadCard inventoryId={activeId} onError={setError} /> : null}
      {activeId ? <CsvUploadCard inventoryId={activeId} onError={setError} /> : null}
    </div>
  );
}

function OcrUploadCard({
  inventoryId,
  onError,
}: {
  inventoryId: string;
  onError: (message: string) => void;
}) {
  const [docKind, setDocKind] = useState("utility_bill");
  const [parser, setParser] = useState("claude");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<S1OcrExtraction | null>(null);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setResult(null);
    try {
      setResult(await scope1Api.ocrExtract(file, docKind, inventoryId, parser));
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload a bill / invoice (OCR)</CardTitle>
        <CardDescription>
          Claude reads the document and extracts the fields. Low-confidence extractions go to the
          review queue; the evidence is stored with a SHA-256 hash.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <Selectable
            value={docKind}
            onChange={setDocKind}
            options={[
              { value: "utility_bill", label: "Utility bill" },
              { value: "fuel_invoice", label: "Fuel invoice" },
            ]}
          />
          <Selectable
            value={parser}
            onChange={setParser}
            options={[
              { value: "claude", label: "Claude OCR (any doc)" },
              { value: "bayou", label: "Bayou (US gas bill · Tier 2)" },
            ]}
          />
          <input type="file" accept=".pdf,image/*" onChange={handleFile} disabled={uploading} className="text-small" />
          {uploading ? <span className="text-small text-muted-foreground">Reading document…</span> : null}
        </div>
        {result ? (
          <Alert>
            <AlertDescription>
              {result.status === "parsing" ? (
                <>
                  <Badge variant="info">Parsing at Bayou</Badge>{" "}
                </>
              ) : result.status === "pending_review" ? (
                <>
                  <Badge variant="medium">Needs review</Badge>{" "}
                </>
              ) : (
                <>
                  <Badge variant="low">Extracted</Badge>{" "}
                </>
              )}
              Sent to the{" "}
              <Link href="/scope-1/review" className="font-medium underline-offset-4 hover:underline">
                review queue
              </Link>
              {result.status === "parsing" ? " — refresh it there once Bayou finishes." : " to verify and create the record."}
            </AlertDescription>
          </Alert>
        ) : null}
      </CardContent>
    </Card>
  );
}

function CsvUploadCard({
  inventoryId,
  onError,
}: {
  inventoryId: string;
  onError: (message: string) => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<S1CsvResult | null>(null);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setResult(null);
    try {
      setResult(await scope1Api.uploadRecordsCsv(inventoryId, file));
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Bulk upload (CSV)</CardTitle>
        <CardDescription>
          Columns: source_name, category (stationary|mobile), fuel, amount, unit — optional
          miles, model_year, tier, biogenic. Each row is calculated on import.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <input type="file" accept=".csv" onChange={handleFile} disabled={uploading} className="text-small" />
        {uploading ? <p className="text-small text-muted-foreground">Importing…</p> : null}
        {result ? (
          <div className="space-y-2 text-small">
            <p>
              <Badge variant="low">{result.created} imported</Badge>
              {result.row_errors.length > 0 ? (
                <Badge variant="high" className="ml-2">
                  {result.row_errors.length} skipped
                </Badge>
              ) : null}
            </p>
            {result.file_errors.map((e, index) => (
              <p key={`f${index}`} className="text-data-high">{e}</p>
            ))}
            {result.row_errors.length > 0 ? (
              <ul className="list-disc space-y-0.5 pl-5 text-caption text-muted-foreground">
                {result.row_errors.map((re) => (
                  <li key={re.row}>
                    Row {re.row}: {re.errors.join("; ")}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

function StationaryForm({
  inventoryId,
  sourceOptions,
  onResult,
  onError,
}: {
  inventoryId: string;
  sourceOptions: { value: string; label: string }[];
  onResult: (record: S1Record) => void;
  onError: (message: string) => void;
}) {
  const year = new Date().getFullYear() - 1;
  const [sourceId, setSourceId] = useState("");
  const [fuel, setFuel] = useState("natural_gas");
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState("therms");
  const [tier, setTier] = useState("4");
  const [evidence, setEvidence] = useState<S1Evidence | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!sourceId || !value) return;
    setSaving(true);
    try {
      const record = await scope1Api.createStationaryRecord({
        inventory_id: inventoryId,
        emission_source_id: sourceId,
        period_start: `${year}-01-01`,
        period_end: `${year}-12-31`,
        fuel_or_activity: fuel,
        activity_value: Number(value),
        activity_unit: unit,
        data_quality_tier: Number(tier),
        evidence_document_id: evidence?.id ?? null,
      });
      onResult(record);
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stationary combustion</CardTitle>
        <CardDescription>Natural gas, diesel, propane and fuel oil burned on site.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Field label="Source">
            <Selectable value={sourceId} onChange={setSourceId} options={sourceOptions} />
          </Field>
          <Field label="Fuel">
            <Selectable
              value={fuel}
              onChange={setFuel}
              options={STATIONARY_FUELS.map((f) => ({ value: f, label: labelFor(f) }))}
            />
          </Field>
          <Field label="Amount">
            <Input type="number" value={value} onChange={(e) => setValue(e.target.value)} />
          </Field>
          <Field label="Unit">
            <Selectable value={unit} onChange={setUnit} options={STATIONARY_UNITS.map((u) => ({ value: u, label: u }))} />
          </Field>
          <Field label="Data quality tier">
            <Selectable value={tier} onChange={setTier} options={["1", "2", "3", "4", "5"].map((t) => ({ value: t, label: `Tier ${t}` }))} />
          </Field>
        </div>
        <EvidenceUploader inventoryId={inventoryId} evidence={evidence} onUploaded={setEvidence} onError={onError} />
        <Button type="button" onClick={submit} disabled={saving || !sourceId || !value}>
          Compute &amp; save
        </Button>
      </CardContent>
    </Card>
  );
}

function EvidenceUploader({
  inventoryId,
  evidence,
  onUploaded,
  onError,
}: {
  inventoryId: string;
  evidence: S1Evidence | null;
  onUploaded: (evidence: S1Evidence) => void;
  onError: (message: string) => void;
}) {
  const [uploading, setUploading] = useState(false);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      onUploaded(await scope1Api.uploadEvidence(file, inventoryId));
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 text-small">
      <Label className="shrink-0">Evidence (optional)</Label>
      <input type="file" onChange={handleFile} disabled={uploading} className="text-caption" />
      {uploading ? <span className="text-muted-foreground">Uploading…</span> : null}
      {evidence ? (
        <span className="text-muted-foreground">
          Attached: {evidence.file_name} · sha256 {evidence.hash_sha256.slice(0, 12)}…
        </span>
      ) : null}
    </div>
  );
}

function MobileForm({
  inventoryId,
  sourceOptions,
  onResult,
  onError,
}: {
  inventoryId: string;
  sourceOptions: { value: string; label: string }[];
  onResult: (record: S1Record) => void;
  onError: (message: string) => void;
}) {
  const year = new Date().getFullYear() - 1;
  const [sourceId, setSourceId] = useState("");
  const [fuel, setFuel] = useState("motor_gasoline");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("gal");
  const [miles, setMiles] = useState("");
  const [modelYear, setModelYear] = useState("");
  const [evidence, setEvidence] = useState<S1Evidence | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!sourceId || !quantity) return;
    setSaving(true);
    try {
      const record = await scope1Api.createMobileRecord({
        inventory_id: inventoryId,
        emission_source_id: sourceId,
        period_start: `${year}-01-01`,
        period_end: `${year}-12-31`,
        fuel_or_activity: fuel,
        fuel_quantity: Number(quantity),
        fuel_unit: unit,
        miles: miles ? Number(miles) : null,
        model_year: modelYear ? Number(modelYear) : null,
        distance_activity: miles ? "gasoline_passenger_car" : null,
        evidence_document_id: evidence?.id ?? null,
      });
      onResult(record);
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Mobile / fleet combustion</CardTitle>
        <CardDescription>
          Fuel drives CO₂; miles + model year drive CH₄/N₂O (optional).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <Field label="Source">
            <Selectable value={sourceId} onChange={setSourceId} options={sourceOptions} />
          </Field>
          <Field label="Fuel">
            <Selectable value={fuel} onChange={setFuel} options={MOBILE_FUELS.map((f) => ({ value: f, label: labelFor(f) }))} />
          </Field>
          <Field label="Fuel amount">
            <Input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
          </Field>
          <Field label="Unit">
            <Selectable value={unit} onChange={setUnit} options={["gal", "scf"].map((u) => ({ value: u, label: u }))} />
          </Field>
          <Field label="Miles (optional)">
            <Input type="number" value={miles} onChange={(e) => setMiles(e.target.value)} />
          </Field>
          <Field label="Model year (optional)">
            <Input type="number" value={modelYear} onChange={(e) => setModelYear(e.target.value)} />
          </Field>
        </div>
        <EvidenceUploader inventoryId={inventoryId} evidence={evidence} onUploaded={setEvidence} onError={onError} />
        <Button type="button" onClick={submit} disabled={saving || !sourceId || !quantity}>
          Compute &amp; save
        </Button>
      </CardContent>
    </Card>
  );
}
