"use client";

import { useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, FileSpreadsheet, Save, UploadCloud } from "lucide-react";

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
import { Textarea } from "@/components/ui/textarea";
import { ModuleIntro } from "@/components/modules/ModuleIntro";
import { AnalyzeResponse, api } from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

export default function AnalyzerPage() {
  const [file, setFile] = useState<File | null>(null);
  const [productName, setProductName] = useState("");
  const [status, setStatus] = useState<"approved" | "flagged">("approved");
  const [flaggedComment, setFlaggedComment] = useState("");
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [savedProductId, setSavedProductId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const topHotspot = useMemo(() => analysis?.result.hotspots[0], [analysis]);

  async function runAnalysis(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    setSavedProductId(null);
    try {
      const response = await api.analyzeBom(file, productName || undefined);
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
      );
      setSavedProductId(response.product_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
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
            <CardDescription>Upload a CSV BOM. The backend performs all parsing, factor matching, and calculations.</CardDescription>
          </CardHeader>
          <CardContent>
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
          </CardContent>
        </Card>

        <div className="space-y-6">
          {loading ? (
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
                  <AlertDescription>Product ID {savedProductId} is now available on the dashboard.</AlertDescription>
                </Alert>
              ) : null}

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
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.result.line_items.map((item) => (
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
                          </tr>
                        ))}
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
    </div>
  );
}
