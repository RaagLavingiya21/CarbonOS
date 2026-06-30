"use client";

import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Factory,
  Loader2,
  Mail,
  Route,
  X,
} from "lucide-react";

import type { Panel } from "@/components/panels/PanelContext";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  api,
  type DraftEmailResponse,
  type EngagementCandidate,
  type RouteResponseResponse,
  type SuppliersListResponse,
} from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

interface SupplierCopilotPanelProps {
  panel: Panel;
  onClose: () => void;
  onStateChange: (partial: Record<string, unknown>) => void;
}

function getCopilotParams(panel: Panel): {
  productName: string;
  topN: number;
} | null {
  if (panel.intake?.module_type === "supplier_copilot") {
    return {
      productName: panel.intake.product_name,
      topN: panel.intake.top_n,
    };
  }

  const productName =
    typeof panel.panel_state.product_name === "string"
      ? panel.panel_state.product_name
      : "";
  const topN =
    typeof panel.panel_state.top_n === "number" ? panel.panel_state.top_n : 5;

  if (!productName) return null;
  return { productName, topN };
}

function candidateKey(candidate: EngagementCandidate): string {
  return `${candidate.supplier_name}-${candidate.component ?? ""}-${candidate.material ?? ""}`;
}

export function SupplierCopilotPanel({
  panel,
  onClose,
  onStateChange,
}: SupplierCopilotPanelProps) {
  const params = getCopilotParams(panel);
  const selectedSupplierKey =
    typeof panel.panel_state.selected_supplier === "string"
      ? panel.panel_state.selected_supplier
      : null;

  const [suppliers, setSuppliers] = useState<SuppliersListResponse | null>(
    null,
  );
  const [selected, setSelected] = useState<EngagementCandidate | null>(null);
  const [draft, setDraft] = useState<DraftEmailResponse | null>(null);
  const [engagementId, setEngagementId] = useState<number | null>(null);
  const [responseText, setResponseText] = useState("");
  const [routing, setRouting] = useState<RouteResponseResponse | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSuppliers = useCallback(async () => {
    if (!params) return;
    setLoading("suppliers");
    setError(null);
    setDraft(null);
    setRouting(null);
    try {
      const response = await api.listSuppliers(params.productName, params.topN);
      setSuppliers(response);
      const restored =
        selectedSupplierKey != null
          ? response.candidates.find(
              (c) => candidateKey(c) === selectedSupplierKey,
            )
          : null;
      const nextSelected = restored ?? response.candidates[0] ?? null;
      setSelected(nextSelected);
      setEngagementId(nextSelected?.existing_engagement_id ?? null);
      onStateChange({
        step: "review",
        product_name: params.productName,
        top_n: params.topN,
        selected_supplier: nextSelected ? candidateKey(nextSelected) : null,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }, [params, selectedSupplierKey, onStateChange]);

  useEffect(() => {
    if (params && !suppliers && loading !== "suppliers") {
      void loadSuppliers();
    }
  }, [params, suppliers, loading, loadSuppliers]);

  function selectCandidate(candidate: EngagementCandidate) {
    setSelected(candidate);
    setDraft(null);
    setRouting(null);
    setEngagementId(candidate.existing_engagement_id);
    onStateChange({
      selected_supplier: candidateKey(candidate),
    });
  }

  async function draftEmail() {
    if (!selected || !params) return;
    setLoading("draft");
    setError(null);
    try {
      setDraft(
        await api.draftEmail(
          params.productName,
          selected,
        ),
      );
      onStateChange({ step: "draft" });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  async function createEngagementRecord() {
    if (!selected || !draft?.draft || !params) return;
    setLoading("engagement");
    setError(null);
    try {
      const response = await api.createEngagement(
        params.productName,
        selected,
        draft.draft.body,
      );
      const id = response.engagement_ids[selected.supplier_name];
      setEngagementId(id);
      onStateChange({ step: "engagement", engagement_id: id });
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
      const result = await api.routeSupplierResponse(
        engagementId,
        selected.supplier_name,
        responseText,
        selected.component,
      );
      setRouting(result);
      onStateChange({ step: "routed" });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(null);
    }
  }

  if (!params) {
    return (
      <PanelShell title="Supplier Copilot" onClose={onClose}>
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Session expired</AlertTitle>
          <AlertDescription>
            Product selection is no longer available. Submit a new Supplier
            Copilot intake form in the chat to start again.
          </AlertDescription>
        </Alert>
      </PanelShell>
    );
  }

  return (
    <PanelShell title="Supplier Copilot" onClose={onClose}>
      <p className="text-sm text-muted-foreground">
        Product: <span className="font-medium text-foreground">{params.productName}</span>
        {" · "}
        Top {params.topN} suppliers
      </p>

      {error ? (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{error}</p>
            <Button size="sm" variant="outline" onClick={() => void loadSuppliers()}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {loading === "suppliers" && !suppliers ? (
        <Card>
          <CardContent className="flex min-h-[160px] flex-col items-center justify-center text-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              Loading supplier candidates...
            </p>
          </CardContent>
        </Card>
      ) : null}

      {suppliers?.error ? (
        <Alert variant="destructive">
          <AlertDescription>{suppliers.error}</AlertDescription>
        </Alert>
      ) : null}

      {suppliers ? (
        <Card>
          <CardHeader>
            <CardTitle>Candidate suppliers</CardTitle>
            <CardDescription>
              Select a supplier to draft outreach and manage engagement.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {suppliers.candidates.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {suppliers.candidates.map((candidate) => (
                  <button
                    key={candidateKey(candidate)}
                    type="button"
                    className={`rounded-xl border bg-card p-4 text-left transition hover:border-primary ${
                      selected && candidateKey(selected) === candidateKey(candidate)
                        ? "border-primary ring-2 ring-primary/20"
                        : ""
                    }`}
                    onClick={() => selectCandidate(candidate)}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="font-medium">{candidate.supplier_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {candidate.component ?? "Component unknown"} /{" "}
                          {candidate.material ?? "Material unknown"}
                        </p>
                      </div>
                      <Badge
                        variant={candidate.contact_found ? "secondary" : "outline"}
                      >
                        {candidate.engagement_status}
                      </Badge>
                    </div>
                    <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <p className="text-muted-foreground">Footprint</p>
                        <p className="font-medium">
                          {formatKg(candidate.kg_co2e)}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Share</p>
                        <p className="font-medium">
                          {formatPct(candidate.share_pct)}
                        </p>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed p-8 text-center">
                <Factory className="mx-auto h-10 w-10 text-muted-foreground" />
                <p className="mt-3 font-medium">No candidates found</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Try a product with saved analysis line items and supplier names.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {selected ? (
        <Card>
          <CardHeader>
            <CardTitle>Draft supplier outreach</CardTitle>
            <CardDescription>{selected.supplier_name}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={() => void draftEmail()} disabled={loading === "draft"}>
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
                  className="min-h-[220px]"
                  value={draft.draft.body}
                  onChange={(event) =>
                    setDraft((current) =>
                      current?.draft
                        ? {
                            ...current,
                            draft: {
                              ...current.draft,
                              body: event.target.value,
                            },
                          }
                        : current,
                    )
                  }
                />
                <p className="text-xs text-muted-foreground">
                  {draft.draft.ghg_protocol_basis}
                </p>
                <Button
                  variant="outline"
                  onClick={() => void createEngagementRecord()}
                  disabled={loading === "engagement"}
                >
                  {loading === "engagement"
                    ? "Saving..."
                    : engagementId
                      ? `Engagement #${engagementId}`
                      : "Create engagement"}
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
            <CardDescription>
              Classify incoming supplier data and decide the next workflow action.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              placeholder="Paste supplier response here..."
              value={responseText}
              onChange={(event) => setResponseText(event.target.value)}
            />
            <Button
              onClick={() => void routeResponse()}
              disabled={loading === "routing" || !responseText.trim()}
            >
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
                      : routing.parsed.error ??
                        "Response parsed without a routing decision."}
                  </p>
                </AlertDescription>
              </Alert>
            ) : null}
          </CardContent>
        </Card>
      ) : null}
    </PanelShell>
  );
}

function PanelShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="text-sm text-muted-foreground">
            Identify hotspots and draft auditable supplier outreach.
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="shrink-0"
          aria-label={`Close ${title}`}
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      {children}
    </div>
  );
}
