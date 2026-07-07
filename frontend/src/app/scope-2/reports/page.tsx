"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Download,
  FileText,
  Plus,
  ShieldCheck,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  BuyerRequest,
  Calculation,
  ComplianceDisclosure,
  DisclosureStandard,
  Report,
  ReportDestination,
  scope2Api,
} from "@/lib/scope2-api";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function download(csv: string, filename: string) {
  downloadBlob(new Blob([csv], { type: "text/csv" }), filename);
}

export default function ReportsPage() {
  const [calcs, setCalcs] = useState<Calculation[]>([]);
  const [destinations, setDestinations] = useState<ReportDestination[]>([]);
  const [calcId, setCalcId] = useState("");
  const [destination, setDestination] = useState("cdp");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [requests, setRequests] = useState<BuyerRequest[]>([]);
  const [buyerName, setBuyerName] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [savingReq, setSavingReq] = useState(false);

  const [standards, setStandards] = useState<DisclosureStandard[]>([]);
  const [standard, setStandard] = useState("sb253");
  const [disclosure, setDisclosure] = useState<ComplianceDisclosure | null>(null);
  const [loadingDisc, setLoadingDisc] = useState(false);

  const loadRequests = useCallback(() => {
    scope2Api.listBuyerRequests().then(setRequests).catch(() => setRequests([]));
  }, []);

  useEffect(() => {
    scope2Api
      .listCalculations()
      .then((c) => {
        setCalcs(c);
        if (c[0]) setCalcId(String(c[0].calc_id));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."));
    scope2Api.reportDestinations().then(setDestinations).catch(() => setDestinations([]));
    scope2Api.disclosureStandards().then(setStandards).catch(() => setStandards([]));
    loadRequests();
  }, [loadRequests]);

  async function addRequest(e: React.FormEvent) {
    e.preventDefault();
    if (!buyerName.trim()) return;
    setSavingReq(true);
    setError(null);
    try {
      await scope2Api.createBuyerRequest({
        buyer_name: buyerName.trim(),
        destination,
        due_date: dueDate || undefined,
      });
      setBuyerName("");
      setDueDate("");
      loadRequests();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add request.");
    } finally {
      setSavingReq(false);
    }
  }

  async function answerRequest(id: number) {
    setError(null);
    try {
      await scope2Api.updateBuyerRequest(id, {
        status: "answered",
        calc_id: calcId ? Number(calcId) : undefined,
      });
      loadRequests();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update.");
    }
  }

  async function removeRequest(id: number) {
    setError(null);
    try {
      await scope2Api.deleteBuyerRequest(id);
      loadRequests();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete.");
    }
  }

  const generate = useCallback(async () => {
    if (!calcId) return;
    setLoading(true);
    setError(null);
    try {
      setReport(await scope2Api.report(Number(calcId), destination));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate report.");
    } finally {
      setLoading(false);
    }
  }, [calcId, destination]);

  const generateDisclosure = useCallback(async () => {
    if (!calcId) return;
    setLoadingDisc(true);
    setError(null);
    try {
      setDisclosure(await scope2Api.disclosure(Number(calcId), standard));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate disclosure.");
    } finally {
      setLoadingDisc(false);
    }
  }, [calcId, standard]);

  async function downloadDisclosure(format: "xlsx" | "pdf") {
    if (!disclosure) return;
    try {
      const blob = await scope2Api.disclosureFile(Number(calcId), disclosure.standard, format);
      downloadBlob(blob, `scope2-${disclosure.standard}-${disclosure.reporting_year}.${format}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed.");
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-6 py-10">
      <Link
        href="/scope-2"
        className="mb-4 inline-flex items-center gap-1 text-small text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Scope 2
      </Link>
      <header className="mb-6">
        <h1 className="text-h1 font-semibold">Buyer &amp; CDP response</h1>
        <p className="text-small text-muted-foreground">
          One number, many formats — prefill CDP and buyer templates from a single
          calculation. Location- and market-based are always reported separately.
        </p>
      </header>

      {error ? <ErrorState title="Something went wrong" message={error} /> : null}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-h3">Inbound requests</CardTitle>
          <CardDescription>
            Track buyer/CDP asks and deadlines. Mark answered once you&apos;ve sent a
            response.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {requests.length > 0 ? (
            <div className="space-y-2">
              {requests.map((r) => (
                <div
                  key={r.request_id}
                  className="flex flex-wrap items-center gap-3 rounded-md border border-border p-3"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{r.buyer_name}</span>
                      <span
                        className={cn(
                          "rounded-md px-1.5 py-0.5 text-caption font-medium capitalize",
                          r.status === "answered"
                            ? "bg-data-low-bg text-data-low"
                            : r.is_overdue
                              ? "bg-data-high-bg text-data-high"
                              : "bg-muted text-muted-foreground",
                        )}
                      >
                        {r.is_overdue && r.status === "open" ? "overdue" : r.status}
                      </span>
                    </div>
                    <div className="text-caption text-muted-foreground">
                      {r.destination}
                      {r.due_date ? ` · due ${r.due_date}` : ""}
                    </div>
                  </div>
                  {r.status === "open" ? (
                    <Button size="sm" variant="secondary" onClick={() => answerRequest(r.request_id)}>
                      Mark answered
                    </Button>
                  ) : null}
                  <Button
                    size="sm"
                    variant="ghost"
                    aria-label="Delete request"
                    onClick={() => removeRequest(r.request_id)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-small text-muted-foreground">No inbound requests yet.</p>
          )}
          <form onSubmit={addRequest} className="flex flex-wrap items-end gap-2 pt-1">
            <div className="min-w-[160px] flex-1 space-y-1.5">
              <Label htmlFor="buyer-name">Buyer</Label>
              <Input
                id="buyer-name"
                value={buyerName}
                onChange={(e) => setBuyerName(e.target.value)}
                placeholder="Walmart"
              />
            </div>
            <div className="w-40 space-y-1.5">
              <Label htmlFor="buyer-due">Due date</Label>
              <Input
                id="buyer-due"
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
            </div>
            <Button type="submit" loading={savingReq} disabled={!buyerName.trim()}>
              <Plus className="h-3.5 w-3.5" /> Add
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-h3">Generate response</CardTitle>
          <CardDescription>Pick a calculation and a destination.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[160px] flex-1 space-y-1.5">
              <Label>Calculation</Label>
              <Select value={calcId} onValueChange={setCalcId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a calculation" />
                </SelectTrigger>
                <SelectContent>
                  {calcs.map((c) => (
                    <SelectItem key={c.calc_id} value={String(c.calc_id)}>
                      #{c.calc_id} · {c.reporting_year}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[160px] flex-1 space-y-1.5">
              <Label>Destination</Label>
              <Select value={destination} onValueChange={setDestination}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {destinations.map((d) => (
                    <SelectItem key={d.key} value={d.key}>
                      {d.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button loading={loading} disabled={!calcId} onClick={generate}>
              <FileText className="h-3.5 w-3.5" /> Generate
            </Button>
          </div>
        </CardContent>
      </Card>

      {report ? (
        <Card className="mt-6">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-h3">{report.entity}</CardTitle>
              <CardDescription>
                {destinations.find((d) => d.key === report.destination)?.label ??
                  report.destination}{" "}
                · {report.reporting_year}
              </CardDescription>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() =>
                download(report.csv, `scope2-${report.destination}-${report.reporting_year}.csv`)
              }
            >
              <Download className="h-3.5 w-3.5" /> CSV
            </Button>
          </CardHeader>
          <CardContent>
            <table className="w-full text-small">
              <tbody>
                {report.rows.map((r) => (
                  <tr key={r.field} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4 text-muted-foreground">{r.field}</td>
                    <td className="num py-2 text-right font-medium">{r.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : null}

      {/* Regulatory disclosures (SB 253 / CSRD ESRS E1) */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-h3">Regulatory disclosure</CardTitle>
          <CardDescription>
            Generate an assurance-ready SB 253 or CSRD ESRS E1 Scope 2 disclosure. Both
            report location- and market-based separately; the readiness check flags gaps
            an assurer will question.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[160px] flex-1 space-y-1.5">
              <Label>Standard</Label>
              <Select value={standard} onValueChange={setStandard}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {standards.map((s) => (
                    <SelectItem key={s.key} value={s.key}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button variant="secondary" loading={loadingDisc} disabled={!calcId} onClick={generateDisclosure}>
              <ShieldCheck className="h-3.5 w-3.5" /> Generate disclosure
            </Button>
          </div>
        </CardContent>
      </Card>

      {disclosure ? (
        <Card className="mt-6">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div>
              <CardTitle className="text-h3">{disclosure.entity}</CardTitle>
              <CardDescription>
                {disclosure.standard_label} · {disclosure.reporting_year}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  download(disclosure.csv, `scope2-${disclosure.standard}-${disclosure.reporting_year}.csv`)
                }
              >
                <Download className="h-3.5 w-3.5" /> CSV
              </Button>
              <Button variant="secondary" size="sm" onClick={() => downloadDisclosure("xlsx")}>
                <Download className="h-3.5 w-3.5" /> XLSX
              </Button>
              <Button variant="secondary" size="sm" onClick={() => downloadDisclosure("pdf")}>
                <Download className="h-3.5 w-3.5" /> PDF
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Readiness banner */}
            <div
              className={cn(
                "flex items-start gap-2 rounded-md border p-3 text-small",
                disclosure.readiness.ready
                  ? "border-data-low/40 bg-data-low-bg/40"
                  : "border-data-high/40 bg-data-high-bg/40",
              )}
            >
              {disclosure.readiness.ready ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-data-low" />
              ) : (
                <AlertTriangle className="mt-0.5 h-4 w-4 text-data-high" />
              )}
              <div className="space-y-1">
                <p className="font-medium">
                  {disclosure.readiness.ready
                    ? "Assurance-ready — no blocking gaps"
                    : "Not assurance-ready"}
                </p>
                {disclosure.readiness.blockers.map((b) => (
                  <p key={b} className="text-data-high">
                    • {b}
                  </p>
                ))}
                {disclosure.readiness.warnings.map((w) => (
                  <p key={w} className="text-data-medium">
                    • {w}
                  </p>
                ))}
              </div>
            </div>

            {disclosure.sections.map((section) => (
              <div key={section.title}>
                <h3 className="mb-1.5 text-caption font-semibold uppercase tracking-wide text-muted-foreground">
                  {section.title}
                </h3>
                <table className="w-full text-small">
                  <tbody>
                    {section.items.map((item) => (
                      <tr key={item.label} className="border-b border-border last:border-0">
                        <td className="py-2 pr-4 text-muted-foreground">
                          {item.label}
                          {item.note ? (
                            <span className="block text-caption text-data-medium">{item.note}</span>
                          ) : null}
                        </td>
                        <td className="num py-2 text-right font-medium">{item.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
