"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Building2, Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { cn } from "@/lib/utils";
import { EstimateResult, LandlordRequest, Site, scope2Api } from "@/lib/scope2-api";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-muted text-muted-foreground",
  sent: "bg-data-info-bg text-data-info",
  responded: "bg-data-low-bg text-data-low",
  declined: "bg-data-high-bg text-data-high",
  overdue: "bg-data-medium-bg text-data-medium",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-1.5 py-0.5 text-caption font-medium capitalize",
        STATUS_STYLES[status] ?? "bg-muted text-muted-foreground",
      )}
    >
      {status}
    </span>
  );
}

export default function LandlordPage() {
  const [requests, setRequests] = useState<LandlordRequest[] | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [siteId, setSiteId] = useState("");
  const [contact, setContact] = useState("");
  const [method, setMethod] = useState("email");
  const [saving, setSaving] = useState(false);

  const [estSite, setEstSite] = useState("");
  const [estArea, setEstArea] = useState("");
  const [estYear, setEstYear] = useState(String(new Date().getFullYear() - 1));
  const [estimating, setEstimating] = useState(false);
  const [estResult, setEstResult] = useState<EstimateResult | null>(null);

  const load = useCallback(() => {
    scope2Api
      .listLandlordRequests()
      .then(setRequests)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load requests."));
  }, []);

  useEffect(() => {
    load();
    scope2Api.listSites().then(setSites).catch(() => setSites([]));
  }, [load]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId) return;
    setSaving(true);
    setError(null);
    try {
      await scope2Api.createLandlordRequest({
        site_id: Number(siteId),
        landlord_contact: contact.trim() || undefined,
        method,
      });
      setSiteId("");
      setContact("");
      setMethod("email");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create request.");
    } finally {
      setSaving(false);
    }
  }

  async function setStatus(id: number, status: string) {
    setError(null);
    try {
      await scope2Api.updateLandlordRequest(id, { status });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update.");
    }
  }

  async function remove(id: number) {
    setError(null);
    try {
      await scope2Api.deleteLandlordRequest(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete.");
    }
  }

  async function runEstimate(e: React.FormEvent) {
    e.preventDefault();
    if (!estSite || !estArea) return;
    setEstimating(true);
    setError(null);
    try {
      setEstResult(
        await scope2Api.estimateSite(Number(estSite), Number(estArea), Number(estYear)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to estimate.");
    } finally {
      setEstimating(false);
    }
  }

  // Landlord-metered sites are the ones that typically need a request.
  const leasedSites = sites.filter(
    (s) => s.ownership === "landlord_metered" || s.ownership === "sub_metered",
  );

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <Link
        href="/scope-2"
        className="mb-4 inline-flex items-center gap-1 text-small text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Scope 2
      </Link>
      <header className="mb-6">
        <h1 className="text-h1 font-semibold">Leased-site data requests</h1>
        <p className="text-small text-muted-foreground">
          Track outreach to landlords for whole-building or sub-metered data — the gap
          no incumbent fills. History persists across staff turnover.
        </p>
      </header>

      {error ? <ErrorState title="Something went wrong" message={error} /> : null}

      <div className="grid gap-6 lg:grid-cols-[1fr,340px]">
        <Card>
          <CardHeader>
            <CardTitle className="text-h3">Request queue</CardTitle>
            <CardDescription>
              Work each request from draft → sent → responded / declined.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {requests === null ? (
              <Skeleton className="h-24 w-full" />
            ) : requests.length === 0 ? (
              <p className="py-6 text-center text-small text-muted-foreground">
                No requests yet. Create one for a landlord-metered site →
              </p>
            ) : (
              <div className="space-y-2">
                {requests.map((r) => (
                  <div
                    key={r.request_id}
                    className="flex flex-wrap items-center gap-3 rounded-md border border-border p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{r.site_name ?? `Site ${r.site_id}`}</span>
                        <StatusBadge status={r.status} />
                      </div>
                      <div className="text-caption text-muted-foreground">
                        {r.landlord_contact ?? "no contact"} · via {r.method}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5">
                      {r.status === "draft" ? (
                        <Button size="sm" variant="secondary" onClick={() => setStatus(r.request_id, "sent")}>
                          Mark sent
                        </Button>
                      ) : null}
                      {r.status === "sent" ? (
                        <>
                          <Button size="sm" variant="secondary" onClick={() => setStatus(r.request_id, "responded")}>
                            Responded
                          </Button>
                          <Button size="sm" variant="ghost" onClick={() => setStatus(r.request_id, "declined")}>
                            Declined
                          </Button>
                        </>
                      ) : null}
                      <Button
                        size="sm"
                        variant="ghost"
                        aria-label="Delete request"
                        onClick={() => remove(r.request_id)}
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-h3">
              <Building2 className="h-4 w-4" /> New request
            </CardTitle>
            <CardDescription>For landlord-metered / sub-metered sites.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={create} className="space-y-3">
              <div className="space-y-1.5">
                <Label>Site</Label>
                <Select value={siteId} onValueChange={setSiteId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a leased site" />
                  </SelectTrigger>
                  <SelectContent>
                    {(leasedSites.length > 0 ? leasedSites : sites).map((s) => (
                      <SelectItem key={s.site_id} value={String(s.site_id)}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ll-contact">Landlord contact</Label>
                <Input
                  id="ll-contact"
                  value={contact}
                  onChange={(e) => setContact(e.target.value)}
                  placeholder="property.mgr@example.com"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Method</Label>
                <Select value={method} onValueChange={setMethod}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="portal">Portal</SelectItem>
                    <SelectItem value="phone">Phone</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Button type="submit" className="w-full" loading={saving} disabled={!siteId}>
                <Plus className="h-3.5 w-3.5" /> Create request
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-h3">Documented estimation fallback</CardTitle>
          <CardDescription>
            When no actual or landlord data is obtainable, estimate from floor area ×
            sector electricity intensity. Saved as an audit-labeled estimate the
            calculation flags — never presented as metered.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={runEstimate} className="flex flex-wrap items-end gap-3">
            <div className="min-w-[180px] flex-1 space-y-1.5">
              <Label>Site</Label>
              <Select value={estSite} onValueChange={setEstSite}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a site" />
                </SelectTrigger>
                <SelectContent>
                  {sites.map((s) => (
                    <SelectItem key={s.site_id} value={String(s.site_id)}>
                      {s.name} ({s.site_type})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-32 space-y-1.5">
              <Label htmlFor="est-area">Floor area (sqft)</Label>
              <Input
                id="est-area"
                value={estArea}
                onChange={(e) => setEstArea(e.target.value)}
                placeholder="20000"
              />
            </div>
            <div className="w-24 space-y-1.5">
              <Label htmlFor="est-year">Year</Label>
              <Input
                id="est-year"
                value={estYear}
                onChange={(e) => setEstYear(e.target.value)}
              />
            </div>
            <Button type="submit" loading={estimating} disabled={!estSite || !estArea}>
              Estimate
            </Button>
          </form>

          {estResult ? (
            <div className="mt-3 rounded-md border border-data-medium/40 bg-data-medium-bg/40 p-3 text-small">
              <span className="num font-semibold">
                {estResult.annual_mwh.toFixed(3)} MWh
              </span>{" "}
              estimated for {estResult.reporting_year} and saved (flagged as estimate).
              <div className="mt-1 text-caption text-muted-foreground">
                {estResult.method_note}
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
