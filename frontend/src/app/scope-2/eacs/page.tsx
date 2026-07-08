"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Award, Plus, Trash2 } from "lucide-react";

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
import { CreateEacPayload, Eac, Site, scope2Api } from "@/lib/scope2-api";

const TYPES = [
  { value: "rec", label: "REC (unbundled)" },
  { value: "go", label: "Guarantee of Origin" },
  { value: "green_tariff", label: "Green tariff" },
  { value: "ppa", label: "PPA" },
];

const CURRENT_YEAR = new Date().getFullYear();

export default function EacsPage() {
  const [eacs, setEacs] = useState<Eac[] | null>(null);
  const [sites, setSites] = useState<Site[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [siteId, setSiteId] = useState("");
  const [type, setType] = useState("rec");
  const [year, setYear] = useState(String(CURRENT_YEAR));
  const [mwh, setMwh] = useState("");
  const [region, setRegion] = useState("");
  const [vintage, setVintage] = useState(String(CURRENT_YEAR));
  const [registry, setRegistry] = useState("");
  const [retirementId, setRetirementId] = useState("");

  const load = useCallback(() => {
    scope2Api
      .listEacs()
      .then(setEacs)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load instruments."));
  }, []);

  useEffect(() => {
    load();
    scope2Api.listSites().then(setSites).catch(() => setSites([]));
  }, [load]);

  // Prefill the market region from the chosen site's eGRID subregion (same-market
  // criterion) — the user can still override.
  function onSiteChange(value: string) {
    setSiteId(value);
    const site = sites.find((s) => String(s.site_id) === value);
    if (site?.egrid_subregion) setRegion(site.egrid_subregion);
  }

  async function addEac(e: React.FormEvent) {
    e.preventDefault();
    if (!siteId || !mwh || !region.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const payload: CreateEacPayload = {
        site_id: Number(siteId),
        instrument_type: type,
        reporting_year: Number(year),
        mwh: Number(mwh),
        region_market: region.trim(),
        vintage_year: Number(vintage),
        registry_name: registry.trim() || undefined,
        retirement_id: retirementId.trim() || undefined,
      };
      await scope2Api.createEac(payload);
      setMwh("");
      setRegistry("");
      setRetirementId("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add instrument.");
    } finally {
      setSaving(false);
    }
  }

  async function removeEac(id: number) {
    setError(null);
    try {
      await scope2Api.deleteEac(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete.");
    }
  }

  const siteName = (id: number) => sites.find((s) => s.site_id === id)?.name ?? `#${id}`;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <Link
        href="/scope-2"
        className="mb-4 inline-flex items-center gap-1 text-small text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Scope 2
      </Link>
      <h1 className="text-h1 font-semibold">EAC registry</h1>
      <p className="mb-6 text-small text-muted-foreground">
        Record the RECs, GOs, green tariffs, and PPAs that back your market-based total. Each is
        screened against the 8 GHG Protocol quality criteria at calculation time; passing
        instruments cover load before residual mix.
      </p>

      {error ? <ErrorState className="mb-6" title="Something went wrong" message={error} /> : null}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Instruments table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-h3">Instruments</CardTitle>
          </CardHeader>
          <CardContent>
            {eacs === null ? (
              <p className="text-small text-muted-foreground">Loading…</p>
            ) : eacs.length === 0 ? (
              <EmptyState
                icon={Award}
                title="No instruments yet"
                description="Add a REC or GO with the form to the right to cover load in the market-based method."
              />
            ) : (
              <div className="overflow-hidden rounded-md border border-border">
                <table className="w-full text-small">
                  <thead className="bg-surface-2 text-caption uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Type</th>
                      <th className="px-3 py-2 text-left font-medium">Site</th>
                      <th className="px-3 py-2 text-right font-medium">MWh</th>
                      <th className="px-3 py-2 text-left font-medium">Region</th>
                      <th className="px-3 py-2 text-right font-medium">Vintage</th>
                      <th className="px-3 py-2 text-left font-medium">Registry</th>
                      <th className="px-3 py-2" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {eacs.map((e) => (
                      <tr key={e.instrument_id} className="hover:bg-secondary/40">
                        <td className="px-3 py-2 font-medium uppercase">{e.instrument_type}</td>
                        <td className="px-3 py-2 text-muted-foreground">{siteName(e.site_id)}</td>
                        <td className="num px-3 py-2 text-right">{e.mwh.toLocaleString()}</td>
                        <td className="px-3 py-2 num text-muted-foreground">{e.region_market}</td>
                        <td className="num px-3 py-2 text-right text-muted-foreground">{e.vintage_year}</td>
                        <td className="px-3 py-2 text-muted-foreground">{e.registry_name ?? "—"}</td>
                        <td className="px-3 py-2 text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="Delete instrument"
                            onClick={() => removeEac(e.instrument_id)}
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

        {/* Add instrument */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="text-h3">Add an instrument</CardTitle>
            <CardDescription>Region prefills from the site&apos;s grid region.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={addEac} className="space-y-3">
              <div className="space-y-1.5">
                <Label>Site</Label>
                <Select value={siteId} onValueChange={onSiteChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select site" />
                  </SelectTrigger>
                  <SelectContent>
                    {sites.map((s) => (
                      <SelectItem key={s.site_id} value={String(s.site_id)}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Instrument type</Label>
                <Select value={type} onValueChange={setType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TYPES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="eac-mwh">MWh</Label>
                  <Input id="eac-mwh" type="number" step="0.001" value={mwh} onChange={(e) => setMwh(e.target.value)} placeholder="500" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="eac-vintage">Vintage year</Label>
                  <Input id="eac-vintage" type="number" value={vintage} onChange={(e) => setVintage(e.target.value)} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="eac-region">Market region</Label>
                  <Input id="eac-region" value={region} onChange={(e) => setRegion(e.target.value)} placeholder="RFCW" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="eac-year">Reporting year</Label>
                  <Input id="eac-year" type="number" value={year} onChange={(e) => setYear(e.target.value)} />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="eac-registry">Registry</Label>
                <Input id="eac-registry" value={registry} onChange={(e) => setRegistry(e.target.value)} placeholder="M-RETS / WREGIS / AIB" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="eac-retire">Retirement ID</Label>
                <Input id="eac-retire" value={retirementId} onChange={(e) => setRetirementId(e.target.value)} placeholder="registry cancellation id" />
              </div>
              <Button type="submit" className="w-full" loading={saving} disabled={!siteId || !mwh || !region.trim()}>
                <Plus className="h-3.5 w-3.5" /> Add instrument
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
