"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, Download, FileUp, Send, Wand2 } from "lucide-react";

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
import {
  QuestionMapping,
  QuestionnaireDetail,
  scope3Api,
} from "@/lib/scope3-api";

function flagVariant(flag: string) {
  if (flag === "auto" || flag === "mapped") return "high" as const;
  if (flag === "needs_human") return "low" as const;
  return "medium" as const;
}

export default function QuestionnaireDetailPage() {
  const params = useParams();
  const requestId = parseInt(params.id as string);

  const [detail, setDetail] = useState<QuestionnaireDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);
  const [mapping, setMapping] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    try {
      const data = await scope3Api.getQuestionnaire(requestId);
      setDetail(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load questionnaire.");
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestId]);

  const handleFile = async (file: File) => {
    setDetecting(true);
    setError(null);
    setNotice(null);
    try {
      const res = await scope3Api.detectQuestionnaire(requestId, file);
      setNotice(
        `Detected ${res.framework} · ${res.question_count} questions` +
          (res.is_low_confidence ? " (low confidence — please review)" : ""),
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to detect questionnaire.");
    } finally {
      setDetecting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleMap = async () => {
    setMapping(true);
    setError(null);
    setNotice(null);
    try {
      const res = await scope3Api.mapQuestionnaire(requestId);
      setNotice(`Mapped ${res.mapped} · ${res.needs_human} need human review`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to map answers.");
    } finally {
      setMapping(false);
    }
  };

  const handleExport = async (format: "csv" | "markdown") => {
    setExporting(true);
    setError(null);
    try {
      const blob = await scope3Api.exportQuestionnaire(requestId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scope3_questionnaire_${requestId}.${format === "csv" ? "csv" : "md"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to export.");
    } finally {
      setExporting(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      await scope3Api.submitQuestionnaire(requestId);
      setNotice("Submitted — confident answers saved to the reusable library.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to submit.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!detail && !error) {
    return (
      <div className="mx-auto w-full max-w-5xl px-6 py-10">
        <Skeleton className="h-[420px] w-full rounded-lg" />
      </div>
    );
  }

  const req = detail?.request;
  const questions = detail?.questions ?? [];
  const mappingByQ = new Map<number, QuestionMapping>(
    (detail?.mappings ?? []).map((m) => [m.question_id, m]),
  );
  const hasQuestions = questions.length > 0;
  const hasMappings = (detail?.mappings ?? []).length > 0;
  const isSubmitted = req?.status === "submitted";

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3/questionnaires" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {req?.customer_name || "Questionnaire"}
          </h1>
          <p className="text-muted-foreground mt-1 text-sm uppercase">
            {req?.framework}
            {req?.deadline ? ` · due ${req.deadline}` : ""}
            {req ? ` · ${req.status.replace(/_/g, " ")}` : ""}
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}
      {notice && (
        <div className="border-primary/30 bg-primary/5 text-foreground mb-6 rounded-md border px-4 py-3 text-sm">
          {notice}
        </div>
      )}

      {!req?.inventory_id && (
        <div className="border-data-medium/40 bg-data-medium-bg text-data-medium mb-6 rounded-md border px-4 py-3 text-sm">
          No inventory attached — mapping needs an inventory to pull answers from. Create
          this request again with an inventory selected, or attach one via the API.
        </div>
      )}

      {/* Step controls */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="text-base">Workflow</CardTitle>
          <CardDescription>
            Upload the questionnaire → auto-detect → map answers from the inventory →
            review → export or submit.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.csv"
            className="hidden"
            onChange={(e) => {
              const file = e.currentTarget.files?.[0];
              if (file) handleFile(file);
            }}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={detecting || isSubmitted}
            >
              <FileUp className="mr-1 h-4 w-4" />
              {detecting ? "Detecting..." : hasQuestions ? "Re-upload" : "Upload & detect"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleMap}
              disabled={mapping || !hasQuestions || !req?.inventory_id || isSubmitted}
            >
              <Wand2 className="mr-1 h-4 w-4" />
              {mapping ? "Mapping..." : "Map answers"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport("csv")}
              disabled={exporting || !hasMappings}
            >
              <Download className="mr-1 h-4 w-4" />
              CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport("markdown")}
              disabled={exporting || !hasMappings}
            >
              <Download className="mr-1 h-4 w-4" />
              Markdown
            </Button>
            <Button
              size="sm"
              onClick={handleSubmit}
              disabled={submitting || !hasMappings || isSubmitted}
            >
              <Send className="mr-1 h-4 w-4" />
              {isSubmitted ? "Submitted" : submitting ? "Submitting..." : "Submit"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Questions + mappings */}
      {hasQuestions ? (
        <div className="space-y-3">
          {questions.map((q) => {
            const m = mappingByQ.get(q.question_id);
            return (
              <Card key={q.question_id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <CardTitle className="text-base font-medium">
                      {q.question_index + 1}. {q.question_text}
                    </CardTitle>
                    {m && (
                      <Badge variant={flagVariant(m.flag_status)} className="capitalize">
                        {m.flag_status.replace(/_/g, " ")}
                      </Badge>
                    )}
                  </div>
                  <CardDescription>
                    {q.question_type}
                    {q.framework_field_key ? ` · ${q.framework_field_key}` : ""}
                  </CardDescription>
                </CardHeader>
                {m && (
                  <CardContent className="space-y-2 text-sm">
                    <p>
                      <span className="text-muted-foreground">Answer: </span>
                      {m.answer_text ?? (
                        <span className="text-muted-foreground italic">
                          needs human review
                        </span>
                      )}
                    </p>
                    <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 text-xs">
                      <span>method: {m.method}</span>
                      <span>confidence: {(m.confidence_score * 100).toFixed(0)}%</span>
                      {m.datapoint_ref && <span>ref: {m.datapoint_ref}</span>}
                      {m.citation && <span>{m.citation}</span>}
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">No questions yet</CardTitle>
            <CardDescription>
              Upload the questionnaire file (.txt or .csv) to detect the framework and
              extract questions.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
