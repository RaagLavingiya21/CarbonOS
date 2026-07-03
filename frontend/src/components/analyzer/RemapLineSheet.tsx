"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { AnalysisLineItem, RemapLineResponse, SectorOption, api } from "@/lib/api";
import { formatKg } from "@/lib/utils";

type RemapLineSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  productId: number;
  lineItem: AnalysisLineItem | null;
  onRemapped?: (result: RemapLineResponse) => void;
};

export function RemapLineSheet({
  open,
  onOpenChange,
  productId,
  lineItem,
  onRemapped,
}: RemapLineSheetProps) {
  const [query, setQuery] = useState("");
  const [sectors, setSectors] = useState<SectorOption[]>([]);
  const [selected, setSelected] = useState<SectorOption | null>(null);
  const [saveOverride, setSaveOverride] = useState(true);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RemapLineResponse | null>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setSelected(null);
      setSaveOverride(true);
      setError(null);
      setResult(null);
      return;
    }
    setSearching(true);
    api
      .searchSectors(lineItem?.matched_sector ?? "")
      .then(setSectors)
      .catch((err) => setError((err as Error).message))
      .finally(() => setSearching(false));
  }, [open, lineItem?.matched_sector]);

  useEffect(() => {
    if (!open) return;
    const handle = window.setTimeout(() => {
      setSearching(true);
      api
        .searchSectors(query)
        .then(setSectors)
        .catch((err) => setError((err as Error).message))
        .finally(() => setSearching(false));
    }, 250);
    return () => window.clearTimeout(handle);
  }, [open, query]);

  async function submitRemap() {
    if (!lineItem?.item_id || !selected) return;
    setLoading(true);
    setError(null);
    try {
      const response = await api.remapLine(productId, lineItem.item_id, selected.sector_code, saveOverride);
      setResult(response);
      onRemapped?.(response);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Re-map emission factor</SheetTitle>
          <SheetDescription>
            Choose a CEDA sector for {lineItem?.material ?? "this material"}. This creates a new
            footprint version — the current version stays unchanged.
          </SheetDescription>
        </SheetHeader>

        {result ? (
          <Alert className="mt-4" variant="success">
            <AlertTitle>Re-map complete</AlertTitle>
            <AlertDescription className="space-y-2">
              <p>
                Created v{result.version}: {formatKg(result.total_kg_co2e_before)} →{" "}
                {formatKg(result.total_kg_co2e_after)} ({result.delta_kg_co2e >= 0 ? "+" : ""}
                {formatKg(result.delta_kg_co2e)})
              </p>
              <Button asChild size="sm" variant="outline">
                <Link href={`/analyzer/${result.new_product_id}`}>View new version</Link>
              </Button>
            </AlertDescription>
          </Alert>
        ) : (
          <div className="mt-4 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="sector-search">Search sectors</Label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="sector-search"
                  className="pl-9"
                  placeholder="e.g. textile, apparel, plastic"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
              </div>
            </div>

            <div className="max-h-64 space-y-2 overflow-y-auto rounded-xl border p-2">
              {searching ? (
                <p className="p-2 text-sm text-muted-foreground">Searching...</p>
              ) : sectors.length === 0 ? (
                <p className="p-2 text-sm text-muted-foreground">No sectors match your search.</p>
              ) : (
                sectors.map((sector) => (
                  <button
                    key={sector.sector_code}
                    className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                      selected?.sector_code === sector.sector_code
                        ? "border-primary bg-accent"
                        : "border-transparent hover:bg-secondary"
                    }`}
                    onClick={() => setSelected(sector)}
                    type="button"
                  >
                    <p className="font-medium">{sector.sector_name}</p>
                    <p className="text-xs text-muted-foreground">{sector.sector_code}</p>
                  </button>
                ))
              )}
            </div>

            <label className="flex items-center gap-2 text-sm">
              <input
                checked={saveOverride}
                onChange={(event) => setSaveOverride(event.target.checked)}
                type="checkbox"
              />
              Save this mapping for our org (future BOMs will use it automatically)
            </label>

            {error ? (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}

            <Button
              disabled={loading || !selected || !lineItem?.item_id}
              onClick={() => void submitRemap()}
              type="button"
            >
              {loading ? "Re-mapping..." : "Re-map and create new version"}
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}

function needsRemap(item: AnalysisLineItem): boolean {
  const flag = item.flag_status ?? "";
  const confidence = item.ef_confidence ?? 100;
  return flag.includes("low_confidence") || flag.includes("unmatched") || confidence < 80;
}

export function lineItemNeedsRemap(item: {
  flag_status?: string;
  ef_confidence?: number | null;
  is_low_confidence?: boolean;
  is_no_ef_match?: boolean;
}): boolean {
  if (item.is_low_confidence || item.is_no_ef_match) return true;
  return needsRemap(item as AnalysisLineItem);
}
