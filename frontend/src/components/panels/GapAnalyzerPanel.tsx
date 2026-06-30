"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Play,
  ShieldCheck,
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
import {
  api,
  type CompanyProfile,
  type GapExecuteResponse,
  type GapPlanResponse,
  type GapReportResponse,
} from "@/lib/api";

type GapStep = "planning" | "executing" | "checkpoint" | "done";

interface GapAnalyzerPanelProps {
  panel: Panel;
  onClose: () => void;
  onStateChange: (partial: Record<string, unknown>) => void;
}

function getGapProfile(panel: Panel): CompanyProfile | null {
  if (panel.intake?.module_type === "gap_analyzer") {
    return {
      name: panel.intake.company_name,
      size: panel.intake.size,
      sector: panel.intake.sector,
      geography: panel.intake.geography,
      products: panel.intake.products,
    };
  }

  const companyName =
    typeof panel.panel_state.company_name === "string"
      ? panel.panel_state.company_name
      : "";
  const sector =
    typeof panel.panel_state.sector === "string" ? panel.panel_state.sector : "";
  const products =
    typeof panel.panel_state.products === "string"
      ? panel.panel_state.products
      : "";

  if (!companyName || !sector || !products) return null;

  return {
    name: companyName,
    size:
      typeof panel.panel_state.size === "string"
        ? panel.panel_state.size
        : "Not specified",
    sector,
    geography:
      typeof panel.panel_state.geography === "string"
        ? panel.panel_state.geography
        : "Not specified",
    products,
  };
}

function getStep(panel: Panel): GapStep {
  const step = panel.panel_state.step;
  if (
    step === "planning" ||
    step === "executing" ||
    step === "checkpoint" ||
    step === "done"
  ) {
    return step;
  }
  return "planning";
}

export function GapAnalyzerPanel({
  panel,
  onClose,
  onStateChange,
}: GapAnalyzerPanelProps) {
  const profile = getGapProfile(panel);
  const step = getStep(panel);
  const sessionId =
    typeof panel.panel_state.session_id === "string"
      ? panel.panel_state.session_id
      : null;

  const [plan, setPlan] = useState<GapPlanResponse | null>(null);
  const [execution, setExecution] = useState<GapExecuteResponse | null>(null);
  const [report, setReport] = useState<GapReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runPlan = useCallback(async () => {
    if (!profile) {
      setError(
        "Company profile is no longer available. Submit a new intake form in the chat.",
      );
      return;
    }
    setLoading(true);
    setError(null);
    onStateChange({ step: "planning" });
    try {
      const response = await api.planGapAnalysis(profile);
      setPlan(response);
      onStateChange({
        step: "executing",
        session_id: response.session_id,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [profile, onStateChange]);

  useEffect(() => {
    if (step === "planning" && profile && !sessionId && !loading && !plan) {
      void runPlan();
    }
  }, [step, profile, sessionId, loading, plan, runPlan]);

  async function executeStep() {
    const activeSessionId = sessionId ?? plan?.session_id;
    if (!activeSessionId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.executeGapStep(activeSessionId);
      setExecution(response);
      if (response.phase === "checkpoint") {
        onStateChange({ step: "checkpoint" });
      } else if (response.phase === "done") {
        onStateChange({ step: "done" });
        setReport(await api.getGapReport(activeSessionId));
      } else {
        onStateChange({ step: "executing" });
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function checkpoint(action: "continue" | "stop") {
    const activeSessionId = sessionId ?? plan?.session_id;
    if (!activeSessionId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.approveGapCheckpoint(activeSessionId, action);
      if (response.phase === "done") {
        onStateChange({ step: "done" });
        setReport(await api.getGapReport(activeSessionId));
      } else {
        onStateChange({ step: "executing" });
      }
      setExecution((current) =>
        current
          ? {
              ...current,
              phase: response.phase,
              current_step: response.current_step,
            }
          : current,
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const results = execution ? Object.values(execution.results) : [];
  const displayStep = execution?.phase === "checkpoint" ? "checkpoint" : step;

  if (!profile && !sessionId) {
    return (
      <PanelShell title="Gap Analyzer" onClose={onClose}>
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Session expired</AlertTitle>
          <AlertDescription>
            The company profile is no longer available. Submit a new Gap Analyzer
            intake form in the chat to start again.
          </AlertDescription>
        </Alert>
      </PanelShell>
    );
  }

  return (
    <PanelShell title="Gap Analyzer" onClose={onClose}>
      {error ? (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{error}</p>
            {profile ? (
              <Button size="sm" variant="outline" onClick={() => void runPlan()}>
                Retry
              </Button>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      {(step === "planning" || (loading && !plan)) && !plan ? (
        <Card>
          <CardContent className="flex min-h-[200px] flex-col items-center justify-center text-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              Generating analysis plan...
            </p>
          </CardContent>
        </Card>
      ) : null}

      {plan ? (
        <Card>
          <CardHeader>
            <CardTitle>Execution plan</CardTitle>
            <CardDescription>
              {profile?.name ?? plan.profile.name} — Session{" "}
              {plan.session_id.slice(0, 8)}…
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {plan.plan.steps.map((planStep, index) => (
              <div
                key={planStep.step_num}
                className="flex gap-4 rounded-xl border bg-card p-4"
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                  {index + 1}
                </div>
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">
                      {planStep.tool_name.replaceAll("_", " ")}
                    </p>
                    {planStep.has_checkpoint_after ? (
                      <Badge variant="outline">Checkpoint after</Badge>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {planStep.rationale}
                  </p>
                </div>
              </div>
            ))}
            <Button
              onClick={() => void executeStep()}
              disabled={loading || displayStep === "done"}
            >
              <Play className="h-4 w-4" />
              {loading
                ? "Running..."
                : execution
                  ? "Run next step"
                  : "Start execution"}
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {displayStep === "checkpoint" ? (
        <Alert>
          <ShieldCheck className="h-4 w-4" />
          <AlertTitle>Human checkpoint</AlertTitle>
          <AlertDescription>
            Review the latest result before continuing the workflow.
            <div className="mt-4 flex flex-wrap gap-3">
              <Button
                size="sm"
                onClick={() => void checkpoint("continue")}
                disabled={loading}
              >
                Approve and continue
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => void checkpoint("stop")}
                disabled={loading}
              >
                Stop workflow
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : null}

      {results.length ? (
        <Card>
          <CardHeader>
            <CardTitle>Executed results</CardTitle>
            <CardDescription>
              Intermediate outputs and citations from completed tools.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {results.map((result) => (
              <div key={result.tool_name} className="rounded-xl border p-4">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-medium">
                    {result.tool_name.replaceAll("_", " ")}
                  </h3>
                  {result.error ? (
                    <Badge variant="destructive">Error</Badge>
                  ) : (
                    <Badge variant="secondary">Complete</Badge>
                  )}
                </div>
                <p className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">
                  {result.error ?? result.content}
                </p>
                {result.citations.length ? (
                  <p className="mt-3 text-xs text-muted-foreground">
                    Sources: {result.citations.join(", ")}
                  </p>
                ) : null}
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}

      {report ? (
        <Alert variant="success">
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Gap analysis complete</AlertTitle>
          <AlertDescription>
            <pre className="mt-3 max-h-[320px] overflow-auto whitespace-pre-wrap rounded-lg bg-card p-4 text-xs text-foreground">
              {report.markdown}
            </pre>
          </AlertDescription>
        </Alert>
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
            Scope 3 gap analysis with human checkpoints.
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
