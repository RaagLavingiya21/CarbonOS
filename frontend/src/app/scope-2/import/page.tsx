"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, CheckCircle2, FileText, Trash2, Upload } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
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
import {
  ConfirmedMeter,
  ExtractDocResult,
  ExtractedMeter,
  ImportDocResult,
  Site,
  scope2Api,
} from "@/lib/scope2-api";

const CARRIERS = [
  { value: "electricity", label: "Electricity" },
  { value: "natural_gas", label: "Natural gas" },
  { value: "steam", label: "Steam" },
  { value: "heat", label: "Heat" },
  { value: "cooling", label: "Cooling" },
];

// A meter the user can edit before committing. Seeded from the extraction; nulls
// become "" so the inputs are controlled.
type Row = {
  energy_carrier: string;
  period_start: string;
  period_end: string;
  raw_quantity: number | null;
  raw_unit: string | null;
  canonical_mwh: number | null;
  cost_usd: number | null;
  is_estimated_read: boolean;
  is_cost_only: boolean;
  needs_review: boolean;
  review_reasons: string[];
  min_confidence: number;
};

function toRow(m: ExtractedMeter): Row {
  return {
    energy_carrier: m.energy_carrier ?? "",
    period_start: m.period_start ?? "",
    period_end: m.period_end ?? "",
    raw_quantity: m.raw_quantity,
    raw_unit: m.raw_unit,
    canonical_mwh: m.canonical_mwh,
    cost_usd: m.cost_usd,
    is_estimated_read: m.is_estimated_read,
    is_cost_only: m.is_cost_only,
    needs_review: m.needs_review,
    review_reasons: m.review_reasons,
    min_confidence: m.min_confidence,
  };
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(new Error("Could not read the file."));
    reader.readAsDataURL(file);
  });
}

export default function Scope2ImportPage() {
  const [sites, setSites] = useState<Site[] | null>(null);
  const [siteId, setSiteId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const [extracting, setExtracting] = useState(false);
  const [extraction, setExtraction] = useState<ExtractDocResult | null>(null);
  const [rows, setRows] = useState<Row[]>([]);

  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<ImportDocResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    scope2Api
      .listSites()
      .then(setSites)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load sites."));
  }, []);

  function updateRow(i: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  function removeRow(i: number) {
    setRows((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function runExtract() {
    if (!file) return;
    setExtracting(true);
    setError(null);
    setResult(null);
    setExtraction(null);
    try {
      const b64 = await fileToBase64(file);
      const res = await scope2Api.extractDoc(b64, file.type || null);
      setExtraction(res);
      setRows(res.meters.map(toRow));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Extraction failed.");
    } finally {
      setExtracting(false);
    }
  }

  async function runImport() {
    if (!siteId || rows.length === 0) return;
    setImporting(true);
    setError(null);
    try {
      const meters: ConfirmedMeter[] = rows.map((r) => ({
        energy_carrier: r.energy_carrier,
        period_start: r.period_start,
        period_end: r.period_end,
        raw_quantity: r.raw_quantity,
        raw_unit: r.raw_unit,
        canonical_mwh: r.canonical_mwh,
        cost_usd: r.cost_usd,
        is_estimated_read: r.is_estimated_read,
        is_cost_only: r.is_cost_only,
      }));
      const res = await scope2Api.importDoc(Number(siteId), meters);
      setResult(res);
      // Clear the staged extraction so the same bill isn't imported twice.
      setExtraction(null);
      setRows([]);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed.");
    } finally {
      setImporting(false);
    }
  }

  const reviewCount = rows.filter((r) => r.needs_review).length;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <Link
        href="/scope-2"
        className="mb-4 inline-flex items-center gap-1 text-small text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Scope 2
      </Link>
      <h1 className="text-h1 font-semibold">Import a bill (PDF/OCR)</h1>
      <p className="mb-6 text-small text-muted-foreground">
        Upload a utility bill; Claude extracts each meter with a confidence score. Review the
        flagged rows, then import — consumption is normalized to MWh and de-duplicated against
        prior estimated reads.
      </p>

      {error ? <ErrorState className="mb-6" title="Something went wrong" message={error} /> : null}

      {result ? (
        <div className="mb-6 flex items-start gap-2 rounded-md border border-data-low/40 bg-data-low-bg/40 p-3 text-small">
          <CheckCircle2 className="mt-0.5 h-4 w-4 text-data-low" />
          <span>
            Imported <span className="num font-semibold text-data-low">{result.committed_count}</span>{" "}
            meter{result.committed_count === 1 ? "" : "s"}.
            {result.superseded_count > 0 ? (
              <> {result.superseded_count} prior estimated read(s) superseded.</>
            ) : null}
            {result.skipped_count > 0 ? (
              <span className="text-data-medium"> {result.skipped_count} skipped (unrecognized carrier).</span>
            ) : null}
          </span>
        </div>
      ) : null}

      {/* Upload */}
      <Card>
        <CardHeader>
          <CardTitle className="text-h3">Upload</CardTitle>
          <CardDescription>PDF or image of a single utility bill (electricity or gas).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-[1fr_1fr]">
            <div className="space-y-1.5">
              <Label>Site</Label>
              <Select value={siteId} onValueChange={setSiteId}>
                <SelectTrigger>
                  <SelectValue placeholder="Which site is this bill for?" />
                </SelectTrigger>
                <SelectContent>
                  {(sites ?? []).map((s) => (
                    <SelectItem key={s.site_id} value={String(s.site_id)}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="bill-file">Bill file</Label>
              <Input
                id="bill-file"
                ref={fileInput}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/*"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
          </div>
          <Button loading={extracting} disabled={!file} onClick={runExtract}>
            <Upload className="h-3.5 w-3.5" /> Extract meters
          </Button>
        </CardContent>
      </Card>

      {/* Review + commit */}
      {extraction ? (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-h3">Review extracted meters</CardTitle>
            <CardDescription>
              {extraction.header.utility_name?.value ? (
                <>Utility: {extraction.header.utility_name.value} · </>
              ) : null}
              {rows.length} meter{rows.length === 1 ? "" : "s"}
              {reviewCount > 0 ? (
                <> · <span className="text-data-medium">{reviewCount} need review</span></>
              ) : null}
              . Edit any field before importing.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {extraction.error ? (
              <div className="rounded-md border border-data-high/40 bg-data-high-bg/40 p-3 text-small text-data-high">
                Extraction error: {extraction.error}
              </div>
            ) : null}

            {rows.length === 0 ? (
              <EmptyState icon={FileText} title="No meters found" description="The model returned no line items for this document." />
            ) : (
              rows.map((r, i) => (
                <div
                  key={i}
                  className={`rounded-md border p-3 ${
                    r.needs_review ? "border-data-medium/50 bg-data-medium-bg/20" : "border-border"
                  }`}
                >
                  <div className="mb-2 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant={r.needs_review ? "medium" : "low"}>
                        {r.needs_review ? "Review" : "OK"}
                      </Badge>
                      <span className="text-caption text-muted-foreground">
                        confidence {(r.min_confidence * 100).toFixed(0)}%
                        {r.canonical_mwh != null ? (
                          <> · <span className="num">{r.canonical_mwh.toFixed(3)} MWh</span></>
                        ) : r.is_cost_only ? (
                          <> · cost-only</>
                        ) : null}
                      </span>
                    </div>
                    <Button variant="ghost" size="icon" aria-label={`Remove meter ${i + 1}`} onClick={() => removeRow(i)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>

                  {r.review_reasons.length > 0 ? (
                    <p className="mb-2 text-caption text-data-medium">{r.review_reasons.join("; ")}</p>
                  ) : null}

                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    <div className="space-y-1">
                      <Label className="text-caption">Carrier</Label>
                      <Select value={r.energy_carrier} onValueChange={(v) => updateRow(i, { energy_carrier: v })}>
                        <SelectTrigger>
                          <SelectValue placeholder="Select" />
                        </SelectTrigger>
                        <SelectContent>
                          {CARRIERS.map((c) => (
                            <SelectItem key={c.value} value={c.value}>
                              {c.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1">
                      <Label className="text-caption">Period start</Label>
                      <Input type="date" value={r.period_start} onChange={(e) => updateRow(i, { period_start: e.target.value })} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-caption">Period end</Label>
                      <Input type="date" value={r.period_end} onChange={(e) => updateRow(i, { period_end: e.target.value })} />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-caption">MWh</Label>
                      <Input
                        type="number"
                        step="0.001"
                        value={r.canonical_mwh ?? ""}
                        onChange={(e) =>
                          updateRow(i, { canonical_mwh: e.target.value === "" ? null : Number(e.target.value) })
                        }
                      />
                    </div>
                  </div>

                  <label className="mt-2 flex items-center gap-2 text-caption text-muted-foreground">
                    <input
                      type="checkbox"
                      checked={r.is_estimated_read}
                      onChange={(e) => updateRow(i, { is_estimated_read: e.target.checked })}
                    />
                    Estimated read
                    {r.raw_quantity != null ? (
                      <span className="ml-auto num">
                        as read: {r.raw_quantity} {r.raw_unit ?? ""}
                      </span>
                    ) : null}
                  </label>
                </div>
              ))
            )}

            <Button loading={importing} disabled={!siteId || rows.length === 0} onClick={runImport}>
              Import {rows.length} meter{rows.length === 1 ? "" : "s"}
            </Button>
            {!siteId ? (
              <p className="text-caption text-data-medium">Select a site above before importing.</p>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
