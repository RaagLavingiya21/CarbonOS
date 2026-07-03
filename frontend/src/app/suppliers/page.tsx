"use client";

import { useState } from "react";
import Link from "next/link";
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
  ApplyPrimaryDataResponse,
  AnalysisLineItem,
  DraftEmailResponse,
  EngagementCandidate,
  RouteResponseResponse,
  SuppliersListResponse,
  api,
} from "@/lib/api";
import { ModuleIntro } from "@/components/modules/ModuleIntro";
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
  const [confirmPrimaryKg, setConfirmPrimaryKg] = useState("");
  const [confirmSourceNote, setConfirmSourceNote] = useState("");
  const [confirmItemId, setConfirmItemId] = useState<number | null>(null);
  const [confirmProductId, setConfirmProductId] = useState<number | null>(null);
  const [applyResult, setApplyResult] = useState<ApplyPrimaryDataResponse | null>(null);
  const [applyingPrimary, setApplyingPrimary] = useState(false);

  async function loadSuppliers(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading("suppliers");
    setError(null);
    setDraft(null);
    setRouting(null);
    setEngagementId(null);
    setApplyResult(null);
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
    setApplyResult(null);
    try {
      const response = await api.routeSupplierResponse(
        engagementId,
        selected.supplier_name,
        responseText,
        selected.component,
      );
      setRouting(response);
      const extracted = response.parsed.parsed?.primary_kg_co2e;
      setConfirmPrimaryKg(extracted != null ? String(extracted) : "");
      setConfirmSourceNote(
        `Supplier response from ${selected.supplier_name} for ${selected.component ?? "component"}`,
      );
      const match = response.suggested_match;
      setConfirmProductId(match?.product_id ?? null);
      if (match?.item_id) {
        setConfirmItemId(match.item_id);
      } else if (match?.matches.length === 1 && match.matches[0].item_id) {
        setConfirmItemId(match.matches[0].item_id);
      } else {
        setConfirmItemId(null);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  async function confirmPrimaryData() {
    if (!confirmProductId || !confirmItemId || !engagementId) return;
    const value = Number(confirmPrimaryKg);
    if (!Number.isFinite(value) || value <= 0 || !confirmSourceNote.trim()) return;
    setApplyingPrimary(true);
    setError(null);
    try {
      const result = await api.applyPrimaryData(confirmProductId, {
        item_id: confirmItemId,
        primary_kg_co2e: value,
        source_note: confirmSourceNote.trim(),
        engagement_id: engagementId,
      });
      setApplyResult(result);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setApplyingPrimary(false);
    }
  }

  function selectMatchCandidate(item: AnalysisLineItem) {
    if (item.item_id) setConfirmItemId(item.item_id);
  }

  const isStoreData =
    routing?.routing?.decision?.action === "store_data" &&
    routing.suggested_match?.product_id != null;

  return (
    <div className="space-y-8">
      <ModuleIntro
        moduleKey="suppliers"
        icon={Factory}
        title="Supplier Engagement Copilot"
        job="Prioritize and reach out to your highest-impact suppliers."
        steps={[
          "Pick a saved product",
          "Rank suppliers by emission impact",
          "Draft a GHG-grounded data request",
        ]}
        needs="A saved product analysis with supplier line items."
      />

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
                {isStoreData ? (
                  <Card>
                    <CardHeader>
                      <CardTitle>Confirm primary data</CardTitle>
                      <CardDescription>
                        Review the extracted supplier value and target line item before applying.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {applyResult ? (
                        <Alert variant="success">
                          <AlertTitle>Primary data applied</AlertTitle>
                          <AlertDescription className="space-y-2">
                            <p>
                              Created v{applyResult.version}, PDS{" "}
                              {formatPct(applyResult.pds_before * 100)} →{" "}
                              {formatPct(applyResult.pds_after * 100)}
                            </p>
                            <Button asChild size="sm" variant="outline">
                              <Link href={`/analyzer/${applyResult.new_product_id}`}>
                                View new version
                              </Link>
                            </Button>
                          </AlertDescription>
                        </Alert>
                      ) : (
                        <>
                          <div className="space-y-2">
                            <Label htmlFor="confirm-primary-kg">Cradle-to-gate kg CO₂e</Label>
                            <Input
                              id="confirm-primary-kg"
                              inputMode="decimal"
                              min="0"
                              type="number"
                              value={confirmPrimaryKg}
                              onChange={(event) => setConfirmPrimaryKg(event.target.value)}
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="confirm-source-note">Source note</Label>
                            <Textarea
                              id="confirm-source-note"
                              value={confirmSourceNote}
                              onChange={(event) => setConfirmSourceNote(event.target.value)}
                            />
                          </div>
                          {(routing.suggested_match?.matches.length ?? 0) > 1 ? (
                            <div className="space-y-2">
                              <Label>Select line item</Label>
                              <div className="grid gap-2">
                                {routing.suggested_match?.matches.map((item) => (
                                  <button
                                    key={`${item.item_id}-${item.component}-${item.material}`}
                                    className={`rounded-lg border p-3 text-left text-sm ${confirmItemId === item.item_id ? "border-primary ring-2 ring-primary/20" : ""}`}
                                    onClick={() => selectMatchCandidate(item)}
                                    type="button"
                                  >
                                    {item.component ?? "Component"} / {item.material ?? "Material"}
                                  </button>
                                ))}
                              </div>
                            </div>
                          ) : routing.suggested_match?.matches.length === 1 ? (
                            <p className="text-sm text-muted-foreground">
                              Target: {routing.suggested_match.matches[0].component} /{" "}
                              {routing.suggested_match.matches[0].material}
                            </p>
                          ) : (
                            <Alert>
                              <AlertDescription>
                                No exact line-item match found. Apply primary data manually from the
                                product detail page.
                              </AlertDescription>
                            </Alert>
                          )}
                          <Button
                            disabled={
                              applyingPrimary ||
                              !confirmProductId ||
                              !confirmItemId ||
                              !confirmPrimaryKg ||
                              Number(confirmPrimaryKg) <= 0 ||
                              !confirmSourceNote.trim()
                            }
                            onClick={confirmPrimaryData}
                            type="button"
                          >
                            {applyingPrimary ? "Applying..." : "Confirm and apply primary data"}
                          </Button>
                        </>
                      )}
                    </CardContent>
                  </Card>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
