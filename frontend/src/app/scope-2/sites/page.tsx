"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Building2, Plus, Trash2 } from "lucide-react";

import { StatusChip } from "@/components/portfolio/StatusChip";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  CsvCommit,
  CsvPreview,
  Site,
  SiteTemplate,
  scope2Api,
} from "@/lib/scope2-api";

const CSV_EXAMPLE =
  "Store,From,To,Usage,Unit,Cost,Estimated\nStore 1,2024-01-01,2024-01-31,12500,kWh,1820.50,false";
const CSV_MAPPING = {
  site_ref: "Store",
  period_start: "From",
  period_end: "To",
  quantity: "Usage",
  unit: "Unit",
  cost_usd: "Cost",
  is_estimated: "Estimated",
};

export default function Scope2SitesPage() {
  const [sites, setSites] = useState<Site[] | null>(null);
  const [templates, setTemplates] = useState<SiteTemplate[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [siteType, setSiteType] = useState("");
  const [zip, setZip] = useState("");
  const [saving, setSaving] = useState(false);

  const [csv, setCsv] = useState(CSV_EXAMPLE);
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState<CsvCommit | null>(null);

  const load = useCallback(() => {
    scope2Api
      .listSites()
      .then(setSites)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load sites."));
  }, []);

  useEffect(() => {
    load();
    scope2Api.siteTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, [load]);

  async function addSite(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !siteType) return;
    setSaving(true);
    setError(null);
    try {
      await scope2Api.createSite({
        name: name.trim(),
        site_type: siteType,
        zip: zip.trim() || undefined,
      });
      setName("");
      setSiteType("");
      setZip("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create site.");
    } finally {
      setSaving(false);
    }
  }

  async function removeSite(siteId: number) {
    try {
      await scope2Api.deleteSite(siteId);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete site.");
    }
  }

  async function runPreview() {
    setPreviewing(true);
    setCommitResult(null);
    try {
      setPreview(await scope2Api.previewCsv(csv, CSV_MAPPING));
    } catch (e) {
      setError(e instanceof Error ? e.message : "CSV preview failed.");
    } finally {
      setPreviewing(false);
    }
  }

  async function runCommit() {
    setCommitting(true);
    setError(null);
    try {
      setCommitResult(await scope2Api.commitCsv(csv, CSV_MAPPING));
    } catch (e) {
      setError(e instanceof Error ? e.message : "CSV import failed.");
    } finally {
      setCommitting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <Link
        href="/scope-2"
        className="mb-4 inline-flex items-center gap-1 text-small text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Scope 2
      </Link>
      <h1 className="text-h1 font-semibold">Sites & utility data</h1>
      <p className="mb-6 text-small text-muted-foreground">
        Add sites from sector templates, then import utility bills.
      </p>

      {error ? <ErrorState className="mb-6" title="Something went wrong" message={error} /> : null}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Sites table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-h3">Sites</CardTitle>
          </CardHeader>
          <CardContent>
            {sites === null ? (
              <Skeleton className="h-40 w-full" />
            ) : sites.length === 0 ? (
              <EmptyState
                icon={Building2}
                title="No sites yet"
                description="Add your first site with the form to the right, or import a bill CSV below."
              />
            ) : (
              <div className="overflow-hidden rounded-md border border-border">
                <table className="w-full text-small">
                  <thead className="bg-surface-2 text-caption uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Name</th>
                      <th className="px-3 py-2 text-left font-medium">Type</th>
                      <th className="px-3 py-2 text-left font-medium">Region</th>
                      <th className="px-3 py-2 text-left font-medium">Status</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {sites.map((site) => (
                      <tr key={site.site_id} className="hover:bg-secondary/40">
                        <td className="px-3 py-2 font-medium">{site.name}</td>
                        <td className="px-3 py-2 text-muted-foreground">{site.site_type}</td>
                        <td className="px-3 py-2 num text-muted-foreground">
                          {site.egrid_subregion ?? site.iea_country ?? site.country ?? "—"}
                        </td>
                        <td className="px-3 py-2">
                          <StatusChip status={site.status} />
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Delete ${site.name}`}
                            onClick={() => removeSite(site.site_id)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Add site */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-h3">Add a site</CardTitle>
            <CardDescription>Boundary + carriers preconfigured from the template.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={addSite} className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="site-name">Name</Label>
                <Input
                  id="site-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Store 1"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Site type</Label>
                <Select value={siteType} onValueChange={setSiteType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select type" />
                  </SelectTrigger>
                  <SelectContent>
                    {templates.map((t) => (
                      <SelectItem key={t.site_type} value={t.site_type}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="site-zip">ZIP (US)</Label>
                <Input
                  id="site-zip"
                  value={zip}
                  onChange={(e) => setZip(e.target.value)}
                  placeholder="10001"
                />
              </div>
              <Button type="submit" className="w-full" loading={saving} disabled={!name.trim() || !siteType}>
                <Plus className="h-3.5 w-3.5" /> Add site
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      {/* CSV import preview */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-h3">Import bills (CSV preview)</CardTitle>
          <CardDescription>
            Expected columns: Store, From, To, Usage, Unit, Cost, Estimated. Consumption is
            normalized to MWh; cost-only rows are flagged, not guessed.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            value={csv}
            onChange={(e) => setCsv(e.target.value)}
            rows={5}
            className="font-mono text-caption"
          />
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" loading={previewing} onClick={runPreview}>
              Preview
            </Button>
            <Button
              size="sm"
              loading={committing}
              disabled={!preview || preview.valid_count === 0}
              onClick={runCommit}
            >
              Import {preview ? preview.valid_count : ""} bills
            </Button>
          </div>

          {commitResult ? (
            <div className="rounded-md border border-data-low/40 bg-data-low-bg/40 p-3 text-small">
              Imported{" "}
              <span className="num font-semibold text-data-low">{commitResult.committed_count}</span>{" "}
              bills.
              {commitResult.unresolved_site_refs.length > 0 ? (
                <span className="text-data-medium">
                  {" "}
                  {commitResult.unresolved_site_refs.length} row(s) skipped — no site named{" "}
                  {commitResult.unresolved_site_refs.map((r) => `"${r}"`).join(", ")}. Add the
                  site first, then re-import.
                </span>
              ) : null}
            </div>
          ) : null}

          {preview ? (
            <div className="rounded-md border border-border p-3 text-small">
              <p className="mb-2">
                <span className="num font-semibold text-data-low">{preview.valid_count}</span> valid ·{" "}
                <span className="num font-semibold text-data-high">{preview.error_count}</span> errors ·{" "}
                <span className="num text-muted-foreground">{preview.total_rows} rows</span>
              </p>
              {preview.bills.map((b, i) => (
                <div key={i} className="flex justify-between border-t border-border py-1 num">
                  <span className="text-muted-foreground">
                    {b.site_ref} · {b.period_start} → {b.period_end}
                  </span>
                  <span>
                    {b.is_cost_only ? (
                      <span className="text-data-medium">cost-only</span>
                    ) : (
                      `${b.canonical_mwh?.toFixed(3)} MWh`
                    )}
                  </span>
                </div>
              ))}
              {preview.errors.map((err) => (
                <div key={err.row_index} className="border-t border-border py-1 text-data-high">
                  Row {err.row_index}: {err.message}
                </div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
