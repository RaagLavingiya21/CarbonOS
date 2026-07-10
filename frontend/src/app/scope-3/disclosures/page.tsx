"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowLeft, ChevronDown, Download, FileText } from "lucide-react";

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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DisclosureDatapoint,
  DisclosureResult,
  InventoryVersion,
  scope3Api,
} from "@/lib/scope3-api";

const FRAMEWORK_LABELS: Record<string, string> = {
  esrs_e1: "ESRS E1",
  sb253: "SB253",
  ifrs_s2: "IFRS S2",
};

function frameworkLabel(f: string) {
  return FRAMEWORK_LABELS[f] ?? f.replace(/_/g, " ").toUpperCase();
}

function flagVariant(flag: string) {
  const f = flag.replace(/[-_]/g, "").toLowerCase();
  if (f === "ok") return "high" as const;
  if (f.includes("provisional")) return "medium" as const;
  return "low" as const;
}

function DatapointRows({ rows }: { rows: DisclosureDatapoint[] }) {
  return (
    <>
      {rows.map((d, i) => (
        <tr key={`${d.key}-${i}`} className="border-b border-border last:border-0">
          <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-muted-foreground">
            {d.key || "—"}
          </td>
          <td className="px-4 py-2.5">{d.label}</td>
          <td
            className={`px-4 py-2.5 ${d.value != null ? "text-right font-mono" : "text-muted-foreground"}`}
          >
            {d.value != null ? (
              d.value.toLocaleString()
            ) : d.text ? (
              d.text
            ) : (
              <span className="text-muted-foreground">—</span>
            )}
          </td>
          <td className="px-4 py-2.5 font-mono text-xs text-muted-foreground">{d.unit}</td>
          <td className="px-4 py-2.5 text-xs text-muted-foreground">
            {d.source_ref || <span className="italic">none</span>}
          </td>
          <td className="px-4 py-2.5">
            <Badge variant={flagVariant(d.flag)}>{d.flag.replace(/_/g, "-")}</Badge>
          </td>
        </tr>
      ))}
    </>
  );
}

export default function DisclosuresPage() {
  const [inventories, setInventories] = useState<InventoryVersion[]>([]);
  const [frameworks, setFrameworks] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [inventoryId, setInventoryId] = useState("");
  const [framework, setFramework] = useState("");
  const [calculating, setCalculating] = useState(false);
  const [result, setResult] = useState<DisclosureResult | null>(null);
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    Promise.all([
      scope3Api.listInventories().catch(() => [] as InventoryVersion[]),
      scope3Api.listFrameworks().catch(() => [] as string[]),
    ])
      .then(([invs, fws]) => {
        setInventories(invs);
        setFrameworks(fws);
        if (invs[0]) setInventoryId(String(invs[0].inventory_id));
        if (fws[0]) setFramework(fws[0]);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."));
  }, []);

  const handleCalculate = async () => {
    if (!inventoryId || !framework) {
      setError("Pick an inventory and a framework.");
      return;
    }
    setCalculating(true);
    setError(null);
    setShowBreakdown(false);
    try {
      setResult(await scope3Api.calculateDisclosure(Number(inventoryId), framework));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to calculate disclosure.");
    } finally {
      setCalculating(false);
    }
  };

  const handleExport = async (format: "csv" | "markdown") => {
    setExporting(true);
    setError(null);
    try {
      const blob = await scope3Api.exportDisclosure(Number(inventoryId), framework, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scope3_${framework}_${inventoryId}.${format === "csv" ? "csv" : "md"}`;
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

  const loadingInputs = inventories.length === 0 && frameworks.length === 0 && !error;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Disclosure</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Framework-ready datapoints from your inventory — every number sourced, never invented.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Generate disclosure</CardTitle>
          <CardDescription>Pick an inventory and a reporting framework.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3">
          {loadingInputs ? (
            <Skeleton className="h-10 w-full" />
          ) : (
            <>
              <div className="min-w-[160px] flex-1">
                <label className="text-muted-foreground text-xs font-medium uppercase">Inventory</label>
                <Select value={inventoryId} onValueChange={setInventoryId}>
                  <SelectTrigger><SelectValue placeholder="Inventory" /></SelectTrigger>
                  <SelectContent>
                    {inventories.map((i) => (
                      <SelectItem key={i.inventory_id} value={String(i.inventory_id)}>
                        {i.reporting_year} · {i.status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="min-w-[160px] flex-1">
                <label className="text-muted-foreground text-xs font-medium uppercase">Framework</label>
                <Select value={framework} onValueChange={setFramework}>
                  <SelectTrigger><SelectValue placeholder="Framework" /></SelectTrigger>
                  <SelectContent>
                    {frameworks.map((f) => (
                      <SelectItem key={f} value={f}>{frameworkLabel(f)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button onClick={handleCalculate} disabled={calculating}>
                {calculating ? "Calculating..." : "Calculate"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {result && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold">
                {frameworkLabel(result.framework)}{" "}
                <span className="text-muted-foreground text-sm font-normal">
                  · format {result.format_version}
                </span>
              </h2>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => handleExport("csv")} disabled={exporting}>
                <Download className="mr-1 h-4 w-4" /> CSV
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExport("markdown")} disabled={exporting}>
                <Download className="mr-1 h-4 w-4" /> Markdown
              </Button>
            </div>
          </div>

          {result.is_provisional && (
            <div className="rounded-md border border-l-2 border-data-medium/40 border-l-data-medium bg-data-medium-bg px-4 py-3 text-sm text-data-medium">
              This framework output is <b>provisional</b> — the reporting format is not yet final.
            </div>
          )}

          <Card className="overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left">
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Key</th>
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Datapoint</th>
                  <th className="px-4 py-2.5 text-right text-xs font-medium uppercase text-muted-foreground">Value</th>
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Unit</th>
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Source</th>
                  <th className="px-4 py-2.5 text-xs font-medium uppercase text-muted-foreground">Flag</th>
                </tr>
              </thead>
              <tbody>
                <DatapointRows rows={result.datapoints} />
              </tbody>
            </table>
          </Card>

          {result.category_breakdown.length > 0 && (
            <Card className="overflow-hidden">
              <button
                type="button"
                onClick={() => setShowBreakdown((s) => !s)}
                className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium"
              >
                <span>
                  Category breakdown{" "}
                  <span className="text-muted-foreground font-normal">
                    · {result.category_breakdown.length} rows
                  </span>
                </span>
                <ChevronDown
                  className={`h-4 w-4 text-muted-foreground transition-transform ${showBreakdown ? "rotate-180" : ""}`}
                />
              </button>
              {showBreakdown && (
                <table className="w-full border-t border-border text-sm">
                  <tbody>
                    <DatapointRows rows={result.category_breakdown} />
                  </tbody>
                </table>
              )}
            </Card>
          )}

          {result.notes.map((n, i) => (
            <p key={i} className="text-muted-foreground flex items-baseline gap-2 text-xs">
              <Badge variant="medium">note</Badge>
              <span>{n}</span>
            </p>
          ))}
        </div>
      )}

      {!result && !loadingInputs && (
        <div className="text-muted-foreground flex items-center gap-2 text-sm">
          <FileText className="h-4 w-4" /> Choose an inventory and framework, then calculate.
        </div>
      )}
    </div>
  );
}
