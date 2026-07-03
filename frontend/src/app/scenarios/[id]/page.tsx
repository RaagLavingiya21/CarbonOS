"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
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
import { Skeleton } from "@/components/ui/skeleton";
import { HotspotBar } from "@/components/data/HotspotBar";
import { MetricCard } from "@/components/data/MetricCard";
import { SourceCitation } from "@/components/data/SourceCitation";
import { ScenarioDetail, ScenarioLineItem, api } from "@/lib/api";
import { formatKg, formatPct } from "@/lib/utils";

function deltaLabel(deltaPct: number | null | undefined) {
  if (deltaPct == null || Number.isNaN(deltaPct)) return "0% vs baseline";
  const prefix = deltaPct > 0 ? "+" : "";
  return `${prefix}${formatPct(deltaPct)} vs baseline`;
}

function lineDeltaKg(item: ScenarioLineItem) {
  const baseline = item.baseline_kg_co2e ?? 0;
  const current = item.kg_co2e ?? 0;
  return current - baseline;
}

export default function ScenarioComparePage({ params }: { params: { id: string } }) {
  const scenarioId = Number(params.id);
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingItemId, setSavingItemId] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<
    Record<number, { material: string; spend_usd: string }>
  >({});

  const loadScenario = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getScenario(scenarioId);
      setScenario(data);
      const nextDrafts: Record<number, { material: string; spend_usd: string }> = {};
      for (const item of data.line_items) {
        if (item.scenario_item_id != null) {
          nextDrafts[item.scenario_item_id] = {
            material: item.material ?? "",
            spend_usd: item.spend_usd != null ? String(item.spend_usd) : "",
          };
        }
      }
      setDrafts(nextDrafts);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [scenarioId]);

  useEffect(() => {
    if (!Number.isFinite(scenarioId)) {
      setError("Invalid scenario ID.");
      setLoading(false);
      return;
    }
    void loadScenario();
  }, [loadScenario, scenarioId]);

  async function saveLineItem(item: ScenarioLineItem) {
    if (item.scenario_item_id == null) return;
    const draft = drafts[item.scenario_item_id];
    if (!draft) return;

    const spend = draft.spend_usd.trim() === "" ? undefined : Number(draft.spend_usd);
    if (spend !== undefined && (!Number.isFinite(spend) || spend < 0)) {
      setError("Spend must be a non-negative number.");
      return;
    }

    const material = draft.material.trim() || undefined;
    const materialChanged = material !== (item.material ?? "");
    const spendChanged = spend !== item.spend_usd;
    if (!materialChanged && !spendChanged) return;

    setSavingItemId(item.scenario_item_id);
    setError(null);
    try {
      const result = await api.editScenarioLineItem(scenarioId, item.scenario_item_id, {
        material: materialChanged ? material : undefined,
        spend_usd: spendChanged ? spend : undefined,
      });
      setScenario((prev) => {
        if (!prev) return prev;
        const lineItems = prev.line_items.map((li) =>
          li.scenario_item_id === item.scenario_item_id ? result.item : li,
        );
        return {
          ...prev,
          total_kg_co2e: result.scenario_total,
          delta_kg: result.delta_kg,
          delta_pct: result.delta_pct,
          line_items: lineItems,
        };
      });
      setDrafts((prev) => ({
        ...prev,
        [item.scenario_item_id!]: {
          material: result.item.material ?? "",
          spend_usd:
            result.item.spend_usd != null ? String(result.item.spend_usd) : "",
        },
      }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSavingItemId(null);
    }
  }

  function updateDraft(
    scenarioItemId: number,
    field: "material" | "spend_usd",
    value: string,
  ) {
    setDrafts((prev) => ({
      ...prev,
      [scenarioItemId]: {
        material: field === "material" ? value : (prev[scenarioItemId]?.material ?? ""),
        spend_usd: field === "spend_usd" ? value : (prev[scenarioItemId]?.spend_usd ?? ""),
      },
    }));
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href={scenario ? `/analyzer/${scenario.baseline_product_id}` : "/"}>
          <ArrowLeft className="h-4 w-4" />
          Back to baseline product
        </Link>
      </Button>

      {loading ? (
        <div className="space-y-6">
          <Skeleton className="h-9 w-64" />
          <div className="grid gap-4 md:grid-cols-3">
            {[1, 2, 3].map((item) => (
              <Skeleton key={item} className="h-24 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-64 rounded-lg" />
        </div>
      ) : error && !scenario ? (
        <ErrorState
          title="Couldn't load this scenario"
          message={error}
          onRetry={() => void loadScenario()}
        />
      ) : scenario ? (
        <>
          <section>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">Scenario</Badge>
              {scenario.delta_pct != null && scenario.delta_pct < 0 ? (
                <Badge variant="default">Reduction</Badge>
              ) : scenario.delta_pct != null && scenario.delta_pct > 0 ? (
                <Badge variant="destructive">Increase</Badge>
              ) : null}
            </div>
            <h1 className="mt-3 text-h1">{scenario.name}</h1>
            <p className="mt-2 text-small text-muted-foreground">
              Baseline product #{scenario.baseline_product_id}
              {scenario.created_at
                ? ` · Created ${new Date(scenario.created_at).toLocaleDateString()}`
                : null}
            </p>
            <p className="mt-1 text-h3 font-semibold text-foreground">
              {deltaLabel(scenario.delta_pct)}
            </p>
          </section>

          {error ? (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}

          <section className="grid gap-4 md:grid-cols-3">
            <MetricCard
              label="Baseline total"
              value={formatKg(scenario.baseline_total_kg_co2e)}
              unit="kg CO₂e"
              hint="Frozen snapshot at scenario creation"
            />
            <MetricCard
              label="Scenario total"
              value={formatKg(scenario.total_kg_co2e)}
              unit="kg CO₂e"
              hint="Recomputed from edited line items"
            />
            <MetricCard
              label="Delta"
              value={formatKg(scenario.delta_kg ?? 0)}
              unit="kg CO₂e"
              hint={deltaLabel(scenario.delta_pct)}
            />
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Line-item comparison</CardTitle>
              <CardDescription>
                Edit material or spend to model changes. Each row shows the delta vs its
                baseline value. Emission factor sources are cited for traceability.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {[...scenario.line_items]
                .sort((a, b) => (b.share_pct ?? 0) - (a.share_pct ?? 0))
                .map((item, index) => {
                  const itemId = item.scenario_item_id;
                  if (itemId == null) return null;
                  const draft = drafts[itemId] ?? {
                    material: item.material ?? "",
                    spend_usd: item.spend_usd != null ? String(item.spend_usd) : "",
                  };
                  const delta = lineDeltaKg(item);

                  return (
                    <div
                      key={itemId}
                      className="space-y-3 rounded-lg border p-4"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <HotspotBar
                          label={item.component ?? "Unnamed component"}
                          sublabel={item.material ?? undefined}
                          sharePct={item.share_pct ?? 0}
                          value={`${formatKg(item.kg_co2e)} kg`}
                          emphasized={index === 0}
                        />
                        {item.is_edited ? (
                          <Badge variant="secondary">Edited</Badge>
                        ) : null}
                      </div>

                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="space-y-1">
                          <label
                            className="text-caption text-muted-foreground"
                            htmlFor={`material-${itemId}`}
                          >
                            Material
                          </label>
                          <Input
                            id={`material-${itemId}`}
                            value={draft.material}
                            onChange={(event) =>
                              updateDraft(itemId, "material", event.target.value)
                            }
                            onBlur={() => void saveLineItem(item)}
                          />
                          {item.baseline_material &&
                          item.baseline_material !== item.material ? (
                            <p className="text-caption text-muted-foreground">
                              Baseline: {item.baseline_material}
                            </p>
                          ) : null}
                        </div>
                        <div className="space-y-1">
                          <label
                            className="text-caption text-muted-foreground"
                            htmlFor={`spend-${itemId}`}
                          >
                            Spend (USD)
                          </label>
                          <Input
                            id={`spend-${itemId}`}
                            inputMode="decimal"
                            min="0"
                            type="number"
                            value={draft.spend_usd}
                            onChange={(event) =>
                              updateDraft(itemId, "spend_usd", event.target.value)
                            }
                            onBlur={() => void saveLineItem(item)}
                          />
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 text-small">
                        <div className="space-y-0.5">
                          <p>
                            Baseline: {formatKg(item.baseline_kg_co2e)} → Scenario:{" "}
                            {formatKg(item.kg_co2e)}
                          </p>
                          <p className="text-muted-foreground">
                            Line delta: {delta >= 0 ? "+" : ""}
                            {formatKg(delta)}
                          </p>
                        </div>
                        <SourceCitation source={item.ef_source ?? ""} />
                      </div>

                      {savingItemId === itemId ? (
                        <p className="text-caption text-muted-foreground">Saving...</p>
                      ) : null}
                    </div>
                  );
                })}
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
