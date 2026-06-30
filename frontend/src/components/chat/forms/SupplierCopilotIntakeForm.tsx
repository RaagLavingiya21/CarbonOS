"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, type AnalysisSummary } from "@/lib/api";
import type { SupplierCopilotIntakePayload } from "@/lib/chat-api";

interface SupplierCopilotIntakeFormProps {
  disabled?: boolean;
  onSubmit: (payload: SupplierCopilotIntakePayload) => void;
}

export function SupplierCopilotIntakeForm({
  disabled = false,
  onSubmit,
}: SupplierCopilotIntakeFormProps) {
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [loadingAnalyses, setLoadingAnalyses] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [productId, setProductId] = useState<string>("");
  const [topN, setTopN] = useState(5);

  useEffect(() => {
    let cancelled = false;
    async function loadAnalyses() {
      setLoadingAnalyses(true);
      setLoadError(null);
      try {
        const results = await api.listAnalyses();
        if (!cancelled) {
          setAnalyses(results);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError((err as Error).message);
        }
      } finally {
        if (!cancelled) {
          setLoadingAnalyses(false);
        }
      }
    }
    void loadAnalyses();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!productId || disabled) return;

    const selected = analyses.find(
      (analysis) => String(analysis.product_id) === productId,
    );
    if (!selected) return;

    onSubmit({
      module_type: "supplier_copilot",
      product_id: selected.product_id,
      product_name: selected.product_name,
      top_n: topN,
    });
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="space-y-2">
        <Label htmlFor="copilot-product">Product</Label>
        <Select
          value={productId}
          onValueChange={setProductId}
          disabled={disabled || loadingAnalyses || analyses.length === 0}
        >
          <SelectTrigger id="copilot-product">
            <SelectValue
              placeholder={
                loadingAnalyses
                  ? "Loading saved analyses..."
                  : analyses.length === 0
                    ? "No saved analyses found"
                    : "Select a product"
              }
            />
          </SelectTrigger>
          <SelectContent>
            {analyses.map((analysis) => (
              <SelectItem
                key={analysis.product_id}
                value={String(analysis.product_id)}
              >
                {analysis.product_name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {loadError ? (
          <p className="text-xs text-destructive">{loadError}</p>
        ) : null}
      </div>
      <div className="space-y-2">
        <Label htmlFor="copilot-top-n">Top N suppliers</Label>
        <Input
          id="copilot-top-n"
          type="number"
          min={1}
          max={20}
          value={topN}
          disabled={disabled}
          onChange={(event) => {
            const value = Number(event.target.value);
            if (Number.isNaN(value)) return;
            setTopN(Math.min(20, Math.max(1, value)));
          }}
        />
      </div>
      <Button
        type="submit"
        disabled={
          disabled ||
          loadingAnalyses ||
          !productId ||
          analyses.length === 0
        }
        className="w-full sm:w-auto"
      >
        Submit
      </Button>
    </form>
  );
}
