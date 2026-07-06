"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Download, FileText, Plus, Trash2 } from "lucide-react";

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
  Report,
  ReportDestination,
  scope2Api,
} from "@/lib/scope2-api";

function download(csv: string, filename: string) {
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
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
    </div>
  );
}
