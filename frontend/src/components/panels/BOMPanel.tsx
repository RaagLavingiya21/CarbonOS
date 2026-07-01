"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Save,
  X,
} from "lucide-react";

import type { Panel } from "@/components/panels/PanelContext";
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
import { Progress } from "@/components/ui/progress";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  type CalculateFootprintResponse,
  type CriticReport,
  type EFMatch,
  type FootprintResult,
  type MatchFactorsResponse,
  type ParsedBom,
} from "@/lib/api";
import type { BomIntakePayload } from "@/lib/chat-api";
import { formatKg, formatPct } from "@/lib/utils";

type BomStep = "parsing" | "bom_review" | "ef_review" | "results" | "saved";

interface BOMPanelProps {
  panel: Panel;
  onClose: () => void;
  onStateChange: (partial: Record<string, unknown>) => void;
}

function getBomIntake(panel: Panel): BomIntakePayload | null {
  if (
    panel.intake?.module_type === "bom_analyzer" &&
    panel.intake.file instanceof File
  ) {
    return panel.intake;
  }
  return null;
}

function getStep(panel: Panel): BomStep {
  const step = panel.panel_state.step;
  if (
    step === "parsing" ||
    step === "bom_review" ||
    step === "ef_review" ||
    step === "results" ||
    step === "saved"
  ) {
    return step;
  }
  return "parsing";
}

export function BOMPanel({ panel, onClose, onStateChange }: BOMPanelProps) {
  const intake = getBomIntake(panel);
  const step = getStep(panel);
  const sessionId =
    typeof panel.panel_state.session_id === "string"
      ? panel.panel_state.session_id
      : null;
  const productName =
    typeof panel.panel_state.product_name === "string"
      ? panel.panel_state.product_name
      : intake?.product_name ?? "";

  const [bom, setBom] = useState<ParsedBom | null>(null);
  const [efMatches, setEfMatches] = useState<(EFMatch | null)[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [result, setResult] = useState<FootprintResult | null>(null);
  const [criticReport, setCriticReport] = useState<CriticReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<"approved" | "flagged">("approved");
  const [flaggedComment, setFlaggedComment] = useState("");
  const [savedProductId, setSavedProductId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const topHotspot = useMemo(() => result?.hotspots[0], [result]);

  const runParse = useCallback(async () => {
    if (!intake?.file) {
      setError("No BOM file available. Submit a new intake form to re-upload.");
      return;
    }
    setLoading(true);
    setError(null);
    onStateChange({ step: "parsing" });
    try {
      const response = await api.parseBom(intake.file, intake.product_name);
      setBom(response.bom);
      onStateChange({
        step: "bom_review",
        session_id: response.session_id,
        product_name: response.bom.product_name,
      });
    } catch (err) {
      setError((err as Error).message);
      onStateChange({ step: "parsing" });
    } finally {
      setLoading(false);
    }
  }, [intake, onStateChange]);

  useEffect(() => {
    if (step === "parsing" && intake?.file && !sessionId && !loading && !bom) {
      void runParse();
    }
    if (step === "bom_review" && intake?.file && sessionId && !bom && !loading) {
      void runParse();
    }
  }, [step, intake, sessionId, loading, bom, runParse]);

  useEffect(() => {
    if (!sessionId) return;

    if (step === "ef_review" && efMatches.length === 0) {
      setLoading(true);
      api
        .matchFactors(sessionId)
        .then((response: MatchFactorsResponse) => {
          setEfMatches(response.ef_matches);
          setWarnings(response.warnings);
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
    }

    if (step === "results" && !result) {
      setLoading(true);
      api
        .calculateFootprint(sessionId)
        .then((response: CalculateFootprintResponse) => {
          setResult(response.result);
          setCriticReport(response.critic_report);
        })
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
    }
    // Only re-run when step/session changes, not when efMatches/result update
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, sessionId]);

  async function handleMatchFactors() {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const response: MatchFactorsResponse = await api.matchFactors(sessionId);
      setEfMatches(response.ef_matches);
      setWarnings(response.warnings);
      onStateChange({ step: "ef_review" });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleCalculate() {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const response: CalculateFootprintResponse =
        await api.calculateFootprint(sessionId);
      setResult(response.result);
      setCriticReport(response.critic_report);
      onStateChange({ step: "results" });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!sessionId || !result) return;
    setSaving(true);
    setError(null);
    try {
      const response = await api.saveAnalysis(
        sessionId,
        productName || result.product_name,
        status,
        status === "flagged" ? flaggedComment : undefined,
      );
      setSavedProductId(response.product_id);
      onStateChange({ step: "saved", product_id: response.product_id });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!intake && !sessionId) {
    return (
      <PanelShell title="BOM Analyzer" onClose={onClose}>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Session expired</AlertTitle>
          <AlertDescription>
            The uploaded file is no longer available. Submit a new BOM intake
            form in the chat to start again.
          </AlertDescription>
        </Alert>
      </PanelShell>
    );
  }

  if (!intake && step === "bom_review" && !bom) {
    return (
      <PanelShell title="BOM Analyzer" onClose={onClose}>
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Session expired</AlertTitle>
          <AlertDescription>
            The uploaded file is no longer available. Submit a new BOM intake
            form in the chat to re-upload and review parsed rows.
          </AlertDescription>
        </Alert>
      </PanelShell>
    );
  }

  return (
    <PanelShell title="BOM Analyzer" onClose={onClose}>
      {error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{error}</p>
            {intake?.file ? (
              <Button size="sm" variant="outline" onClick={() => void runParse()}>
                Retry
              </Button>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {(step === "parsing" || loading) && !bom ? (
        <Card>
          <CardContent className="flex min-h-[200px] flex-col items-center justify-center text-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              Parsing BOM file...
            </p>
          </CardContent>
        </Card>
      ) : null}

      {step === "bom_review" && bom ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle>BOM review</CardTitle>
              <CardDescription>
                Review parsed rows and flags before matching emission factors.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {bom.file_errors.length ? (
                <Alert variant="destructive">
                  <AlertTitle>File errors</AlertTitle>
                  <AlertDescription>
                    {bom.file_errors.map((msg) => (
                      <p key={msg}>{msg}</p>
                    ))}
                  </AlertDescription>
                </Alert>
              ) : null}

              <div className="overflow-x-auto rounded-xl border">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <thead className="bg-secondary text-muted-foreground">
                    <tr>
                      <th className="px-4 py-3">#</th>
                      <th className="px-4 py-3">Component</th>
                      <th className="px-4 py-3">Material</th>
                      <th className="px-4 py-3">Spend (USD)</th>
                      <th className="px-4 py-3">Flags</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bom.rows.map((row) => (
                      <tr key={row.row_index} className="border-t bg-card">
                        <td className="px-4 py-3">{row.row_index + 1}</td>
                        <td className="px-4 py-3">{row.component ?? "-"}</td>
                        <td className="px-4 py-3">{row.material ?? "-"}</td>
                        <td className="px-4 py-3">
                          {row.spend_usd != null ? row.spend_usd.toFixed(2) : "-"}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex flex-wrap gap-1">
                            {row.flags.length ? (
                              row.flags.map((flag) => (
                                <Badge
                                  key={`${flag.row_index}-${flag.field}-${flag.flag_type}`}
                                  variant={
                                    flag.severity === "error"
                                      ? "destructive"
                                      : "secondary"
                                  }
                                >
                                  {flag.message}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-muted-foreground">-</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <Button
                disabled={loading || !bom.is_valid}
                onClick={() => void handleMatchFactors()}
              >
                {loading ? "Matching..." : "Match emission factors"}
              </Button>
            </CardContent>
          </Card>
        </>
      ) : null}

      {step === "ef_review" ? (
        <Card>
          <CardHeader>
            <CardTitle>Emission factor review</CardTitle>
            <CardDescription>
              Review matched factors and warnings before calculating footprint.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {warnings.length ? (
              <Alert>
                <AlertTitle>Warnings</AlertTitle>
                <AlertDescription>
                  {warnings.map((warning) => (
                    <p key={warning} className="mt-1">
                      {warning}
                    </p>
                  ))}
                </AlertDescription>
              </Alert>
            ) : null}

            <div className="space-y-3">
              {efMatches.map((match, index) => (
                <div
                  key={index}
                  className="rounded-xl border bg-card p-4 text-sm"
                >
                  {match ? (
                    <>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{match.material_input}</p>
                        <Badge
                          variant={
                            match.is_no_match || match.is_low_confidence
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {Math.round(match.confidence_score)}%
                        </Badge>
                      </div>
                      <p className="mt-1 text-muted-foreground">
                        {match.sector_name} ({match.sector_code}) —{" "}
                        {match.ef_kg_co2e_per_usd} kg CO2e/USD
                      </p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Source: {match.source_citation}
                      </p>
                      {match.suggested_alternatives.length ? (
                        <p className="mt-1 text-xs text-muted-foreground">
                          Alternatives:{" "}
                          {match.suggested_alternatives.join(", ")}
                        </p>
                      ) : null}
                    </>
                  ) : (
                    <p className="text-muted-foreground">
                      Row {index + 1}: no match
                    </p>
                  )}
                </div>
              ))}
            </div>

            <Button disabled={loading} onClick={() => void handleCalculate()}>
              {loading ? "Calculating..." : "Calculate footprint"}
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {step === "results" || step === "saved" ? (
        result ? (
          <>
            <section className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardDescription>Total footprint</CardDescription>
                  <CardTitle className="text-2xl">
                    {formatKg(result.total_kg_co2e)}
                  </CardTitle>
                </CardHeader>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Completeness</CardDescription>
                  <CardTitle className="text-2xl">
                    {formatPct(result.completeness_pct)}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Progress value={result.completeness_pct} />
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardDescription>Flagged items</CardDescription>
                  <CardTitle className="text-2xl">{result.flagged_count}</CardTitle>
                </CardHeader>
              </Card>
            </section>

            {savedProductId ? (
              <Alert variant="success">
                <CheckCircle2 className="h-4 w-4" />
                <AlertTitle>Analysis saved</AlertTitle>
                <AlertDescription>
                  Product ID {savedProductId} is now available on the dashboard.
                </AlertDescription>
              </Alert>
            ) : null}

            {warnings.length || criticReport?.has_findings ? (
              <Alert>
                <AlertTitle>Review required</AlertTitle>
                <AlertDescription>
                  {[
                    ...warnings,
                    ...(criticReport?.findings.map((f) => f.message) ?? []),
                  ]
                    .slice(0, 5)
                    .map((warning) => (
                      <p key={warning} className="mt-1">
                        {warning}
                      </p>
                    ))}
                </AlertDescription>
              </Alert>
            ) : null}

            <Card>
              <CardHeader>
                <CardTitle>Hotspots</CardTitle>
                <CardDescription>
                  {topHotspot
                    ? `${topHotspot.component ?? topHotspot.material} is the largest contributor.`
                    : "No hotspot available."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.hotspots.map((item) => (
                  <div
                    key={`${item.row_index}-${item.material}`}
                    className="rounded-xl border p-4"
                  >
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="font-medium">
                          {item.component ?? "Unnamed component"}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {item.material ?? "Unknown material"} {"-> "}
                          {item.sector_name}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold">{formatKg(item.kg_co2e)}</p>
                        <p className="text-sm text-muted-foreground">
                          {formatPct(item.share_pct)} of total
                        </p>
                      </div>
                    </div>
                    <Progress
                      className="mt-3"
                      value={Math.min(item.share_pct, 100)}
                    />
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Line-item results</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto rounded-xl border">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="bg-secondary text-muted-foreground">
                      <tr>
                        <th className="px-4 py-3">Component</th>
                        <th className="px-4 py-3">Material</th>
                        <th className="px-4 py-3">Sector</th>
                        <th className="px-4 py-3">kg CO2e</th>
                        <th className="px-4 py-3">Confidence</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.line_items.map((item) => (
                        <tr key={item.row_index} className="border-t bg-card">
                          <td className="px-4 py-3">{item.component ?? "-"}</td>
                          <td className="px-4 py-3">{item.material ?? "-"}</td>
                          <td className="px-4 py-3">{item.sector_name}</td>
                          <td className="px-4 py-3 font-medium">
                            {formatKg(item.kg_co2e)}
                          </td>
                          <td className="px-4 py-3">
                            <Badge
                              variant={
                                item.is_low_confidence || item.is_no_ef_match
                                  ? "destructive"
                                  : "secondary"
                              }
                            >
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

            {step !== "saved" ? (
              <Card>
                <CardHeader>
                  <CardTitle>Human review checkpoint</CardTitle>
                  <CardDescription>
                    Save the analysis as approved or flagged.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Button
                      variant={status === "approved" ? "default" : "outline"}
                      onClick={() => setStatus("approved")}
                    >
                      Approved
                    </Button>
                    <Button
                      variant={status === "flagged" ? "default" : "outline"}
                      onClick={() => setStatus("flagged")}
                    >
                      Flag for review
                    </Button>
                  </div>
                  {status === "flagged" ? (
                    <Textarea
                      placeholder="Explain what needs analyst review."
                      value={flaggedComment}
                      onChange={(event) => setFlaggedComment(event.target.value)}
                    />
                  ) : null}
                  <Button
                    disabled={
                      saving ||
                      (status === "flagged" && !flaggedComment.trim())
                    }
                    onClick={() => void handleSave()}
                  >
                    <Save className="h-4 w-4" />
                    {saving ? "Saving..." : "Save analysis"}
                  </Button>
                </CardContent>
              </Card>
            ) : null}
          </>
        ) : null
      ) : null}
    </PanelShell>
  );
}

function PanelShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="text-sm text-muted-foreground">
            Review parsed data and complete the footprint workflow.
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="shrink-0"
          aria-label={`Close ${title}`}
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      {children}
    </div>
  );
}
