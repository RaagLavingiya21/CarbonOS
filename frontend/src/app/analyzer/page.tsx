"use client";

import Link from "next/link";
import { useMemo, useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { AlertCircle, CheckCircle2, Copy, Download, FileSpreadsheet, Save, UploadCloud } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";
import { ModuleIntro } from "@/components/modules/ModuleIntro";
import { RemapLineSheet, lineItemNeedsRemap } from "@/components/analyzer/RemapLineSheet";
import { AnalyzeResponse, AnalysisDetail, AnalysisLineItem, BulkAnalyzeResponse, api } from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

type ImportMode = "single" | "bulk";

function reportingDatesFromYear(year: number | ""): { start?: string; end?: string } {
  if (!year) return {};
  return {
    start: `${year}-01-01`,
    end: `${year}-12-31`,
  };
}

export default function AnalyzerPage() {
  return (
    <Suspense fallback={null}>
      <AnalyzerPageContent />
    </Suspense>
  );
}

function AnalyzerPageContent() {
  const searchParams = useSearchParams();
  const [importMode, setImportMode] = useState<ImportMode>("single");
  const [file, setFile] = useState<File | null>(null);
  const [bulkFiles, setBulkFiles] = useState<File[]>([]);
  const [bulkResults, setBulkResults] = useState<BulkAnalyzeResponse | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [productName, setProductName] = useState("");
  const [recalculateOfProductId, setRecalculateOfProductId] = useState<number | null>(null);
  const [savedVersion, setSavedVersion] = useState<number | null>(null);
  const [productDescription, setProductDescription] = useState("");
  const [reportingYear, setReportingYear] = useState<number | "">(new Date().getFullYear());
  const [geographyCountry, setGeographyCountry] = useState("");
  const [status, setStatus] = useState<"approved" | "flagged">("approved");
  const [flaggedComment, setFlaggedComment] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [savedProductId, setSavedProductId] = useState<number | null>(null);
  const [savedAnalysisDetail, setSavedAnalysisDetail] = useState<AnalysisDetail | null>(null);
  const [remapOpen, setRemapOpen] = useState(false);
  const [remapLineItem, setRemapLineItem] = useState<AnalysisLineItem | null>(null);
  const [savedAsApproved, setSavedAsApproved] = useState(false);
  const [pactPayload, setPactPayload] = useState<Record<string, unknown> | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const recalculateOf = searchParams.get("recalculate_of");
    const nameFromUrl = searchParams.get("product_name");
    if (recalculateOf) {
      const parsed = Number(recalculateOf);
      if (!Number.isNaN(parsed)) {
        setRecalculateOfProductId(parsed);
      }
    }
    if (nameFromUrl) {
      setProductName(nameFromUrl);
    }
  }, [searchParams]);

  const topHotspot = useMemo(() => analysis?.result.hotspots[0], [analysis]);
  const intakeOptions = useMemo(() => {
    const dates = reportingDatesFromYear(reportingYear);
    return {
      productDescription: productDescription.trim() || undefined,
      reportingPeriodStart: dates.start,
      reportingPeriodEnd: dates.end,
      geographyCountry: geographyCountry.trim().toUpperCase() || undefined,
    };
  }, [productDescription, reportingYear, geographyCountry]);

  async function runBulkAnalysis(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (bulkFiles.length === 0) return;
    setBulkLoading(true);
    setError(null);
    setBulkResults(null);
    try {
      const response = await api.analyzeBulk(bulkFiles);
      setBulkResults(response);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBulkLoading(false);
    }
  }

  async function runAnalysis(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    setSavedProductId(null);
    setSavedAnalysisDetail(null);
    setSavedAsApproved(false);
    setSavedVersion(null);
    setPactPayload(null);
    try {
      const response = await api.analyzeBom(file, productName || undefined, intakeOptions);
      setAnalysis(response);
      setProductName(response.result.product_name);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function saveResult() {
    if (!analysis) return;
    setSaving(true);
    setError(null);
    try {
      const response = await api.saveAnalysis(
        analysis.session_id,
        productName || analysis.result.product_name,
        status,
        status === "flagged" ? flaggedComment : undefined,
        {
          ...intakeOptions,
          recalculateOfProductId: recalculateOfProductId ?? undefined,
        },
      );
      setSavedProductId(response.product_id);
      setSavedAsApproved(status === "approved");
      const saved = await api.getAnalysis(String(response.product_id));
      setSavedAnalysisDetail(saved);
      if (recalculateOfProductId) {
        setSavedVersion(saved.version ?? null);
      } else {
        setSavedVersion(null);
      }
      setPactPayload(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function exportPactPayload() {
    if (!savedProductId) return;
    setExportLoading(true);
    setError(null);
    try {
      const payload = await api.fetchPactPayload(savedProductId);
      setPactPayload(payload);
      setExportOpen(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExportLoading(false);
    }
  }

  const pactJson = pactPayload ? JSON.stringify(pactPayload, null, 2) : "";

  async function copyPactJson() {
    if (!pactJson) return;
    await navigator.clipboard.writeText(pactJson);
  }

  function downloadPactJson() {
    if (!pactJson || !savedProductId) return;
    const blob = new Blob([pactJson], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `footprint-${savedProductId}-pact.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-8">
      <ModuleIntro
        moduleKey="analyzer"
        icon={UploadCloud}
        title="BOM Analyzer"
        job="Estimate a product's footprint from its bill of materials."
        steps={[
          "Upload a BOM CSV",
          "Review parsed rows and matched emission factors",
          "Get the footprint and emission hotspots",
        ]}
        needs="A CSV with columns: component, material, quantity, spend_usd."
      />

      {error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Analyzer error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Analysis input</CardTitle>
            <CardDescription>
              Upload one BOM CSV or import multiple files in one batch. The backend performs all parsing, factor matching, and calculations.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4 grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant={importMode === "single" ? "default" : "outline"}
                onClick={() => setImportMode("single")}
              >
                Single product
              </Button>
              <Button
                type="button"
                variant={importMode === "bulk" ? "default" : "outline"}
                onClick={() => setImportMode("bulk")}
              >
                Bulk import
              </Button>
            </div>

            {importMode === "single" ? (
            <form className="space-y-4" onSubmit={runAnalysis}>
              <div className="space-y-2">
                <Label htmlFor="product-name">Product name</Label>
                <Input
                  id="product-name"
                  placeholder="e.g. Refillable shampoo bottle"
                  value={productName}
                  onChange={(event) => setProductName(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="product-description">Product description (optional)</Label>
                <Textarea
                  id="product-description"
                  placeholder="Brief description for PACT export metadata"
                  value={productDescription}
                  onChange={(event) => setProductDescription(event.target.value)}
                  rows={2}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="reporting-year">Reporting year (optional)</Label>
                  <Input
                    id="reporting-year"
                    type="number"
                    min={2000}
                    max={2100}
                    value={reportingYear}
                    onChange={(event) =>
                      setReportingYear(event.target.value ? Number(event.target.value) : "")
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="geography-country">Country code (optional)</Label>
                  <Input
                    id="geography-country"
                    placeholder="US"
                    maxLength={2}
                    value={geographyCountry}
                    onChange={(event) => setGeographyCountry(event.target.value.toUpperCase())}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="bom-file">BOM CSV</Label>
                <Input
                  id="bom-file"
                  type="file"
                  accept=".csv,text/csv"
                  required
                  onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                />
              </div>
              <Button className="w-full" disabled={loading || !file} type="submit">
                <UploadCloud className="h-4 w-4" />
                {loading ? "Analyzing..." : "Run analysis"}
              </Button>
            </form>
            ) : (
            <form className="space-y-4" onSubmit={runBulkAnalysis}>
              <div className="space-y-2">
                <Label htmlFor="bulk-bom-files">BOM CSV files</Label>
                <Input
                  id="bulk-bom-files"
                  type="file"
                  accept=".csv,text/csv"
                  multiple
                  required
                  onChange={(event) => setBulkFiles(Array.from(event.target.files ?? []))}
                />
                <p className="text-xs text-muted-foreground">
                  Each file becomes one product. One bad file will not stop the rest.
                </p>
              </div>
              <Button className="w-full" disabled={bulkLoading || bulkFiles.length === 0} type="submit">
                <UploadCloud className="h-4 w-4" />
                {bulkLoading
                  ? "Analyzing..."
                  : `Analyze ${bulkFiles.length || 0} file${bulkFiles.length === 1 ? "" : "s"}`}
              </Button>
            </form>
            )}
          </CardContent>
        </Card>

        <div className="space-y-6">
          {importMode === "bulk" ? (
            bulkLoading ? (
              <Card>
                <CardContent className="flex min-h-[360px] flex-col items-center justify-center text-center">
                  <div className="mb-6 h-16 w-16 animate-pulse rounded-2xl bg-accent" />
                  <h3 className="text-lg font-medium">Running bulk footprint workflow</h3>
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    FastAPI is processing each BOM file independently and saving successful analyses.
                  </p>
                </CardContent>
              </Card>
            ) : bulkResults ? (
              <>
                <section className="grid gap-4 md:grid-cols-4">
                  <Card>
                    <CardHeader>
                      <CardDescription>Total files</CardDescription>
                      <CardTitle className="text-3xl">{bulkResults.summary.total}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardDescription>Saved</CardDescription>
                      <CardTitle className="text-3xl">{bulkResults.summary.saved}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardDescription>Flagged</CardDescription>
                      <CardTitle className="text-3xl">{bulkResults.summary.flagged}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader>
                      <CardDescription>Errors</CardDescription>
                      <CardTitle className="text-3xl">{bulkResults.summary.error}</CardTitle>
                    </CardHeader>
                  </Card>
                </section>

                <Card>
                  <CardHeader>
                    <CardTitle>Bulk import results</CardTitle>
                    <CardDescription>
                      Each saved product opens in the analyzer detail view for review.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto rounded-xl border">
                      <table className="w-full min-w-[720px] text-left text-sm">
                        <thead className="bg-secondary text-muted-foreground">
                          <tr>
                            <th className="px-4 py-3">Filename</th>
                            <th className="px-4 py-3">Product</th>
                            <th className="px-4 py-3">Total kg CO2e</th>
                            <th className="px-4 py-3">Flagged items</th>
                            <th className="px-4 py-3">Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {bulkResults.results.map((row) => (
                            <tr key={row.filename} className="border-t bg-card">
                              <td className="px-4 py-3 font-medium">{row.filename}</td>
                              <td className="px-4 py-3">
                                {row.status === "saved" && row.product_id ? (
                                  <Link
                                    className="text-primary underline-offset-4 hover:underline"
                                    href={`/analyzer/${row.product_id}`}
                                  >
                                    {row.product_name ?? `Product ${row.product_id}`}
                                  </Link>
                                ) : (
                                  "-"
                                )}
                              </td>
                              <td className="px-4 py-3">
                                {row.total_kg_co2e != null ? formatKg(row.total_kg_co2e) : "-"}
                              </td>
                              <td className="px-4 py-3">
                                {row.flagged_items != null ? row.flagged_items : "-"}
                              </td>
                              <td className="px-4 py-3">
                                {row.status === "saved" ? (
                                  <Badge variant={(row.flagged_items ?? 0) > 0 ? "destructive" : "secondary"}>
                                    {(row.flagged_items ?? 0) > 0 ? "Saved (flagged)" : "Saved"}
                                  </Badge>
                                ) : (
                                  <Badge variant="destructive" title={row.error ?? undefined}>
                                    Error
                                  </Badge>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {bulkResults.results.some((row) => row.status === "error") ? (
                      <div className="mt-4 space-y-2">
                        {bulkResults.results
                          .filter((row) => row.status === "error")
                          .map((row) => (
                            <Alert key={`${row.filename}-error`} variant="destructive">
                              <AlertTitle>{row.filename}</AlertTitle>
                              <AlertDescription>{row.error}</AlertDescription>
                            </Alert>
                          ))}
                      </div>
                    ) : null}
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card>
                <CardContent className="flex min-h-[360px] flex-col items-center justify-center text-center">
                  <FileSpreadsheet className="h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-medium">Awaiting bulk BOM upload</h3>
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    Drop multiple CSV files to create several products in one pass. Results will appear here with links to each saved analysis.
                  </p>
                </CardContent>
              </Card>
            )
          ) : loading ? (
            <Card>
              <CardContent className="flex min-h-[360px] flex-col items-center justify-center text-center">
                <div className="mb-6 h-16 w-16 animate-pulse rounded-2xl bg-accent" />
                <h3 className="text-lg font-medium">Running footprint workflow</h3>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">
                  FastAPI is parsing the BOM, matching emission factors, calculating line-item emissions, and running the critic.
                </p>
              </CardContent>
            </Card>
          ) : analysis ? (
            <>
              <section className="grid gap-4 md:grid-cols-4">
                <Card className="md:col-span-2">
                  <CardHeader>
                    <CardDescription>Total footprint</CardDescription>
                    <CardTitle className="text-3xl">{formatKg(analysis.result.total_kg_co2e)}</CardTitle>
                  </CardHeader>
                </Card>
                <Card className="">
                  <CardHeader>
                    <CardDescription>Completeness</CardDescription>
                    <CardTitle className="text-3xl">{formatPct(analysis.result.completeness_pct)}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Progress value={analysis.result.completeness_pct} />
                  </CardContent>
                </Card>
                <Card className="">
                  <CardHeader>
                    <CardDescription>Flagged items</CardDescription>
                    <CardTitle className="text-3xl">{analysis.result.flagged_count}</CardTitle>
                  </CardHeader>
                </Card>
              </section>

              {savedProductId ? (
                <Alert variant="success">
                  <CheckCircle2 className="h-4 w-4" />
                  <AlertTitle>Analysis saved</AlertTitle>
                  <AlertDescription>
                    Product ID {savedProductId} is now available on the dashboard.
                    {savedVersion && recalculateOfProductId ? (
                      <span className="mt-1 block">
                        This is version {savedVersion} of {productName || analysis.result.product_name}.
                      </span>
                    ) : null}
                    {savedAsApproved ? (
                      <span className="mt-2 block">
                        <Button
                          className="mt-2"
                          disabled={exportLoading}
                          onClick={exportPactPayload}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          <Download className="h-4 w-4" />
                          {exportLoading ? "Loading PACT payload..." : "Export PACT payload"}
                        </Button>
                      </span>
                    ) : null}
                  </AlertDescription>
                </Alert>
              ) : null}

              <Sheet open={exportOpen} onOpenChange={setExportOpen}>
                <SheetContent className="w-full overflow-y-auto sm:max-w-2xl">
                  <SheetHeader>
                    <SheetTitle>PACT v3 ProductFootprint</SheetTitle>
                    <SheetDescription>
                      Preview and download the exported payload for product {savedProductId}.
                    </SheetDescription>
                  </SheetHeader>
                  <div className="mt-4 space-y-3">
                    <div className="flex gap-2">
                      <Button onClick={copyPactJson} size="sm" type="button" variant="outline">
                        <Copy className="h-4 w-4" />
                        Copy JSON
                      </Button>
                      <Button onClick={downloadPactJson} size="sm" type="button" variant="outline">
                        <Download className="h-4 w-4" />
                        Download .json
                      </Button>
                    </div>
                    <pre className="max-h-[70vh] overflow-auto rounded-xl border bg-secondary p-4 text-xs">
                      {pactJson}
                    </pre>
                  </div>
                </SheetContent>
              </Sheet>

              {analysis.warnings.length || analysis.critic_report.has_findings ? (
                <Alert>
                  <AlertTitle>Review required</AlertTitle>
                  <AlertDescription>
                    {[...analysis.warnings, ...analysis.critic_report.findings.map((finding) => finding.message)].slice(0, 5).map((warning) => (
                      <p key={warning} className="mt-1">{warning}</p>
                    ))}
                  </AlertDescription>
                </Alert>
              ) : null}

              <Card>
                <CardHeader>
                  <CardTitle>Hotspots</CardTitle>
                  <CardDescription>
                    {topHotspot
                      ? `${topHotspot.component ?? topHotspot.material} is currently the largest contributor.`
                      : "No hotspot available for this analysis."}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {analysis.result.hotspots.map((item) => (
                    <div key={`${item.row_index}-${item.material}`} className="rounded-xl border p-4">
                      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                        <div>
                          <p className="font-medium">{item.component ?? "Unnamed component"}</p>
                          <p className="text-sm text-muted-foreground">
                            {item.material ?? "Unknown material"} {"->"} {item.sector_name}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-semibold">{formatKg(item.kg_co2e)}</p>
                          <p className="text-sm text-muted-foreground">{formatPct(item.share_pct)} of total</p>
                        </div>
                      </div>
                      <Progress className="mt-3" value={Math.min(item.share_pct, 100)} />
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Line-item results</CardTitle>
                  <CardDescription>Traceable emissions by BOM row and matched factor source.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto rounded-xl border">
                    <table className="w-full min-w-[860px] text-left text-sm">
                      <thead className="bg-secondary text-muted-foreground">
                        <tr>
                          <th className="px-4 py-3">Component</th>
                          <th className="px-4 py-3">Material</th>
                          <th className="px-4 py-3">Supplier</th>
                          <th className="px-4 py-3">Sector</th>
                          <th className="px-4 py-3">kg CO2e</th>
                          <th className="px-4 py-3">Confidence</th>
                          {savedProductId ? <th className="px-4 py-3">Actions</th> : null}
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.result.line_items.map((item) => {
                          const savedItem = savedAnalysisDetail?.line_items.find(
                            (row) =>
                              row.material === item.material && row.component === item.component,
                          );
                          return (
                          <tr key={item.row_index} className="border-t bg-card">
                            <td className="px-4 py-3">{item.component ?? "-"}</td>
                            <td className="px-4 py-3">{item.material ?? "-"}</td>
                            <td className="px-4 py-3">{item.supplier ?? "-"}</td>
                            <td className="px-4 py-3">{item.sector_name}</td>
                            <td className="px-4 py-3 font-medium">{formatKg(item.kg_co2e)}</td>
                            <td className="px-4 py-3">
                              <Badge variant={item.is_low_confidence || item.is_no_ef_match ? "destructive" : "secondary"}>
                                {Math.round(item.ef_confidence)}%
                              </Badge>
                            </td>
                            {savedProductId ? (
                              <td className="px-4 py-3">
                                {savedItem?.item_id && lineItemNeedsRemap(item) ? (
                                  <Button
                                    onClick={() => {
                                      setRemapLineItem(savedItem);
                                      setRemapOpen(true);
                                    }}
                                    size="sm"
                                    type="button"
                                    variant="outline"
                                  >
                                    Re-map
                                  </Button>
                                ) : (
                                  "-"
                                )}
                              </td>
                            ) : null}
                          </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Human review checkpoint</CardTitle>
                  <CardDescription>Save the analysis as approved or flagged with reviewer context.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Button variant={status === "approved" ? "default" : "outline"} onClick={() => setStatus("approved")}>
                      Approved
                    </Button>
                    <Button variant={status === "flagged" ? "default" : "outline"} onClick={() => setStatus("flagged")}>
                      Flag for review
                    </Button>
                  </div>
                  {status === "flagged" ? (
                    <Textarea
                      placeholder="Explain what needs analyst review before downstream use."
                      value={flaggedComment}
                      onChange={(event) => setFlaggedComment(event.target.value)}
                    />
                  ) : null}
                  <Button
                    disabled={saving || (status === "flagged" && !flaggedComment.trim())}
                    onClick={saveResult}
                  >
                    <Save className="h-4 w-4" />
                    {saving ? "Saving..." : "Save analysis"}
                  </Button>
                </CardContent>
              </Card>
            </>
          ) : (
            <Card>
              <CardContent className="flex min-h-[360px] flex-col items-center justify-center text-center">
                <FileSpreadsheet className="h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">Awaiting BOM upload</h3>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">
                  Results, factor warnings, critic findings, and save controls will appear here after analysis.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {savedProductId ? (
        <RemapLineSheet
          lineItem={remapLineItem}
          onOpenChange={setRemapOpen}
          open={remapOpen}
          productId={savedProductId}
          onRemapped={async (result) => {
            const refreshed = await api.getAnalysis(String(result.new_product_id));
            setSavedProductId(result.new_product_id);
            setSavedAnalysisDetail(refreshed);
            setSavedVersion(refreshed.version ?? null);
          }}
        />
      ) : null}
    </div>
  );
}
