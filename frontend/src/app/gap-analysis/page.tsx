"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardList, FileSearch, Play, ShieldCheck } from "lucide-react";

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
import { Textarea } from "@/components/ui/textarea";
import {
  CompanyProfile,
  GapExecuteResponse,
  GapPlanResponse,
  GapReportResponse,
  api,
} from "@/lib/api";
import { ModuleIntro } from "@/components/modules/ModuleIntro";

export default function GapAnalysisPage() {
  const [profile, setProfile] = useState<CompanyProfile>({
    name: "",
    size: "500-5,000 employees",
    sector: "",
    geography: "",
    products: "",
  });
  const [plan, setPlan] = useState<GapPlanResponse | null>(null);
  const [execution, setExecution] = useState<GapExecuteResponse | null>(null);
  const [report, setReport] = useState<GapReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateProfile(field: keyof CompanyProfile, value: string) {
    setProfile((current) => ({ ...current, [field]: value }));
  }

  async function createPlan(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setExecution(null);
    setReport(null);
    try {
      const response = await api.planGapAnalysis(profile);
      setPlan(response);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function executeStep() {
    if (!plan) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.executeGapStep(plan.session_id);
      setExecution(response);
      if (response.phase === "done") {
        setReport(await api.getGapReport(plan.session_id));
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  async function checkpoint(action: "continue" | "stop") {
    if (!plan) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.approveGapCheckpoint(plan.session_id, action);
      if (response.phase === "done") {
        setReport(await api.getGapReport(plan.session_id));
      }
      setExecution((current) =>
        current ? { ...current, phase: response.phase, current_step: response.current_step } : current,
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const results = execution ? Object.values(execution.results) : [];

  return (
    <div className="space-y-8">
      <ModuleIntro
        moduleKey="gap"
        icon={FileSearch}
        title="Scope 3 Gap Analyzer"
        job="Assess your Scope 3 reporting readiness and find data gaps."
        steps={[
          "Describe your company",
          "Review the generated assessment plan",
          "Get data gaps and recommendations",
        ]}
        needs="Basic company details: size, sector, geography, and products."
      />

      {error ? (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Gap analysis error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Company profile</CardTitle>
            <CardDescription>Used by the backend planner to decide the execution sequence.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={createPlan}>
              <div className="space-y-2">
                <Label htmlFor="company">Company</Label>
                <Input id="company" value={profile.name} onChange={(event) => updateProfile("name", event.target.value)} placeholder="Company name" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sector">Sector</Label>
                <Input id="sector" required value={profile.sector} onChange={(event) => updateProfile("sector", event.target.value)} placeholder="Consumer goods" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="size">Company size</Label>
                <Input id="size" value={profile.size} onChange={(event) => updateProfile("size", event.target.value)} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="geography">Geography</Label>
                <Input id="geography" value={profile.geography} onChange={(event) => updateProfile("geography", event.target.value)} placeholder="North America, EU" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="products">Products / services</Label>
                <Textarea id="products" required value={profile.products} onChange={(event) => updateProfile("products", event.target.value)} placeholder="Describe major product categories and purchased goods." />
              </div>
              <Button className="w-full" disabled={loading}>
                <ClipboardList className="h-4 w-4" />
                {loading && !plan ? "Planning..." : "Generate plan"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          {plan ? (
            <Card>
              <CardHeader>
                <CardTitle>Execution plan</CardTitle>
                <CardDescription>Session {plan.session_id}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {plan.plan.steps.map((step, index) => (
                  <div key={step.step_num} className="flex gap-4 rounded-xl border bg-card p-4">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                      {index + 1}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="font-medium">{step.tool_name.replaceAll("_", " ")}</p>
                        {step.has_checkpoint_after ? <Badge variant="outline">Checkpoint after</Badge> : null}
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">{step.rationale}</p>
                    </div>
                  </div>
                ))}
                <Button onClick={executeStep} disabled={loading || execution?.phase === "done"}>
                  <Play className="h-4 w-4" />
                  {loading ? "Running..." : execution ? "Run next step" : "Start execution"}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="flex min-h-[320px] flex-col items-center justify-center text-center">
                <ClipboardList className="h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No plan yet</h3>
                <p className="mt-2 max-w-md text-sm text-muted-foreground">Fill out the company profile to create the gap-analysis execution plan.</p>
              </CardContent>
            </Card>
          )}

          {execution?.phase === "checkpoint" ? (
            <Alert>
              <ShieldCheck className="h-4 w-4" />
              <AlertTitle>Human checkpoint</AlertTitle>
              <AlertDescription>
                Review the latest result before continuing the workflow.
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button size="sm" onClick={() => checkpoint("continue")} disabled={loading}>Approve and continue</Button>
                  <Button size="sm" variant="outline" onClick={() => checkpoint("stop")} disabled={loading}>Stop workflow</Button>
                </div>
              </AlertDescription>
            </Alert>
          ) : null}

          {results.length ? (
            <Card>
              <CardHeader>
                <CardTitle>Executed results</CardTitle>
                <CardDescription>Intermediate outputs and citations from completed tools.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {results.map((result) => (
                  <div key={result.tool_name} className="rounded-xl border p-4">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-medium">{result.tool_name.replaceAll("_", " ")}</h3>
                      {result.error ? <Badge variant="destructive">Error</Badge> : <Badge variant="secondary">Complete</Badge>}
                    </div>
                    <p className="mt-3 whitespace-pre-wrap text-sm text-muted-foreground">{result.error ?? result.content}</p>
                    {result.citations.length ? (
                      <p className="mt-3 text-xs text-muted-foreground">Sources: {result.citations.join(", ")}</p>
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
                <pre className="mt-3 max-h-[420px] overflow-auto whitespace-pre-wrap rounded-lg bg-card p-4 text-xs text-foreground">
                  {report.markdown}
                </pre>
              </AlertDescription>
            </Alert>
          ) : null}
        </div>
      </div>
    </div>
  );
}
