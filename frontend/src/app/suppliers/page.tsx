"use client";

import { useState } from "react";
import { Factory, Mail, Route, Search } from "lucide-react";

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
  DraftEmailResponse,
  EngagementCandidate,
  RouteResponseResponse,
  SuppliersListResponse,
  api,
} from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

export default function SuppliersPage() {
  const [productName, setProductName] = useState("");
  const [suppliers, setSuppliers] = useState<SuppliersListResponse | null>(null);
  const [selected, setSelected] = useState<EngagementCandidate | null>(null);
  const [draft, setDraft] = useState<DraftEmailResponse | null>(null);
  const [engagementId, setEngagementId] = useState<number | null>(null);
  const [responseText, setResponseText] = useState("");
  const [routing, setRouting] = useState<RouteResponseResponse | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadSuppliers(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading("suppliers");
    setError(null);
    setDraft(null);
    setRouting(null);
    setEngagementId(null);
    try {
      const response = await api.listSuppliers(productName);
      setSuppliers(response);
      setSelected(response.candidates[0] ?? null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  async function draftEmail() {
    if (!selected) return;
    setLoading("draft");
    setError(null);
    try {
      setDraft(await api.draftEmail(productName || suppliers?.product_name || "", selected));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  async function createEngagement() {
    if (!selected || !draft?.draft) return;
    setLoading("engagement");
    setError(null);
    try {
      const response = await api.createEngagement(
        productName || suppliers?.product_name || "",
        selected,
        draft.draft.body,
      );
      setEngagementId(response.engagement_ids[selected.supplier_name]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  async function routeResponse() {
    if (!selected || !engagementId || !responseText.trim()) return;
    setLoading("routing");
    setError(null);
    try {
      setRouting(
        await api.routeSupplierResponse(
          engagementId,
          selected.supplier_name,
          responseText,
          selected.component,
        ),
      );
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="space-y-8">
      <section>
        <Badge variant="secondary">Supplier engagement</Badge>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight md:text-4xl">
          Supplier copilot
        </h1>
        <p className="mt-3 max-w-2xl text-muted-foreground">
          Identify high-impact suppliers, draft auditable outreach, create engagement records, and route supplier responses through the backend graph.
        </p>
      </section>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Supplier copilot error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[420px_1fr]">
        <Card className="h-fit">
          <CardHeader>
            <CardTitle>Find suppliers</CardTitle>
            <CardDescription>Pull supplier candidates from saved product analyses.</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={loadSuppliers}>
              <div className="space-y-2">
                <Label htmlFor="product-name">Product name</Label>
                <Input
                  id="product-name"
                  required
                  value={productName}
                  onChange={(event) => setProductName(event.target.value)}
                  placeholder="Saved product name"
                />
              </div>
              <Button className="w-full" disabled={loading === "suppliers"}>
                <Search className="h-4 w-4" />
                {loading === "suppliers" ? "Finding suppliers..." : "Find candidates"}
              </Button>
            </form>

            {suppliers?.error ? (
              <Alert className="mt-4" variant="destructive">
                <AlertDescription>{suppliers.error}</AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Candidate suppliers</CardTitle>
              <CardDescription>Select a supplier to draft outreach.</CardDescription>
            </CardHeader>
            <CardContent>
              {suppliers ? (
                suppliers.candidates.length ? (
                  <div className="grid gap-3 md:grid-cols-2">
                    {suppliers.candidates.map((candidate) => (
                      <button
                        key={`${candidate.supplier_name}-${candidate.component}`}
                        className={`rounded-xl border bg-card p-4 text-left transition hover:border-primary ${selected?.supplier_name === candidate.supplier_name ? "border-primary ring-2 ring-primary/20" : ""}`}
                        onClick={() => {
                          setSelected(candidate);
                          setDraft(null);
                          setRouting(null);
                          setEngagementId(candidate.existing_engagement_id);
                        }}
                        type="button"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">{candidate.supplier_name}</p>
                            <p className="text-sm text-muted-foreground">{candidate.component ?? "Component unknown"} / {candidate.material ?? "Material unknown"}</p>
                          </div>
                          <Badge variant={candidate.contact_found ? "secondary" : "outline"}>
                            {candidate.engagement_status}
                          </Badge>
                        </div>
                        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <p className="text-muted-foreground">Footprint</p>
                            <p className="font-medium">{formatKg(candidate.kg_co2e)}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground">Share</p>
                            <p className="font-medium">{formatPct(candidate.share_pct)}</p>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed p-8 text-center">
                    <Factory className="mx-auto h-10 w-10 text-muted-foreground" />
                    <p className="mt-3 font-medium">No candidates found</p>
                    <p className="mt-1 text-sm text-muted-foreground">Try a product with saved analysis line items and supplier names.</p>
                  </div>
                )
              ) : (
                <div className="rounded-xl border border-dashed p-8 text-center">
                  <Factory className="mx-auto h-10 w-10 text-muted-foreground" />
                  <p className="mt-3 font-medium">Search for a product to begin</p>
                </div>
              )}
            </CardContent>
          </Card>

          {selected ? (
            <Card>
              <CardHeader>
                <CardTitle>Draft supplier outreach</CardTitle>
                <CardDescription>{selected.supplier_name}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Button onClick={draftEmail} disabled={loading === "draft"}>
                  <Mail className="h-4 w-4" />
                  {loading === "draft" ? "Drafting..." : "Draft email"}
                </Button>
                {draft?.error ? (
                  <Alert variant="destructive">
                    <AlertDescription>{draft.error}</AlertDescription>
                  </Alert>
                ) : null}
                {draft?.draft ? (
                  <div className="space-y-3 rounded-xl border bg-card p-4">
                    <div>
                      <Label>To</Label>
                      <p className="mt-1 text-sm">{draft.draft.to}</p>
                    </div>
                    <div>
                      <Label>Subject</Label>
                      <p className="mt-1 text-sm font-medium">{draft.draft.subject}</p>
                    </div>
                    <Textarea
                      className="min-h-[260px]"
                      value={draft.draft.body}
                      onChange={(event) =>
                        setDraft((current) =>
                          current?.draft
                            ? { ...current, draft: { ...current.draft, body: event.target.value } }
                            : current,
                        )
                      }
                    />
                    <p className="text-xs text-muted-foreground">{draft.draft.ghg_protocol_basis}</p>
                    <Button variant="outline" onClick={createEngagement} disabled={loading === "engagement"}>
                      {loading === "engagement" ? "Saving..." : engagementId ? `Engagement #${engagementId}` : "Create engagement"}
                    </Button>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          {engagementId && selected ? (
            <Card>
              <CardHeader>
                <CardTitle>Route supplier response</CardTitle>
                <CardDescription>Classify incoming supplier data and decide the next workflow action.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
                  placeholder="Paste supplier response here..."
                  value={responseText}
                  onChange={(event) => setResponseText(event.target.value)}
                />
                <Button onClick={routeResponse} disabled={loading === "routing" || !responseText.trim()}>
                  <Route className="h-4 w-4" />
                  {loading === "routing" ? "Routing..." : "Route response"}
                </Button>
                {routing ? (
                  <Alert variant="success">
                    <AlertTitle>Routing decision</AlertTitle>
                    <AlertDescription>
                      <p>Status: {routing.engagement_status}</p>
                      <p className="mt-2">
                        {routing.routing?.decision
                          ? `${routing.routing.decision.action}: ${routing.routing.decision.rationale}`
                          : routing.parsed.error ?? "Response parsed without a routing decision."}
                      </p>
                    </AlertDescription>
                  </Alert>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
