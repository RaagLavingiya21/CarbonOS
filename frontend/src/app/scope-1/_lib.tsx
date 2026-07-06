"use client";

// Shared helpers for the Scope 1 section (not a route — underscore-prefixed).

import { useCallback, useEffect, useState } from "react";

import { scope1Api, type S1Inventory } from "@/lib/scope1-api";
import { cn } from "@/lib/utils";

const ACTIVE_KEY = "s1-active-inventory";

export function fmtT(value?: number | null): string {
  return (value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 3 });
}

export function useInventories() {
  const [inventories, setInventories] = useState<S1Inventory[]>([]);
  const [activeId, setActiveIdState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inv = await scope1Api.listInventories();
      setInventories(inv);
      setActiveIdState((current) => {
        const stored =
          current ??
          (typeof window !== "undefined" ? window.localStorage.getItem(ACTIVE_KEY) : null);
        if (stored && inv.some((i) => i.id === stored)) return stored;
        return inv[0]?.id ?? null;
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const setActiveId = useCallback((id: string) => {
    setActiveIdState(id);
    try {
      window.localStorage.setItem(ACTIVE_KEY, id);
    } catch {
      // ignore persistence failures
    }
  }, []);

  const active = inventories.find((i) => i.id === activeId) ?? null;
  return { inventories, active, activeId, setActiveId, loading, error, reload: load };
}

export function InventoryPicker({
  inventories,
  activeId,
  onChange,
}: {
  inventories: S1Inventory[];
  activeId: string | null;
  onChange: (id: string) => void;
}) {
  if (inventories.length === 0) return null;
  return (
    <select
      value={activeId ?? ""}
      onChange={(event) => onChange(event.target.value)}
      className="h-9 rounded-md border bg-card px-3 text-small"
      aria-label="Active inventory"
    >
      {inventories.map((inv) => (
        <option key={inv.id} value={inv.id}>
          {inv.reporting_year} · {inv.consolidation_approach.replace(/_/g, " ")}
          {inv.locked ? " · locked" : ""}
        </option>
      ))}
    </select>
  );
}

export function ArToggle({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="inline-flex rounded-md border p-0.5" role="group" aria-label="GWP version">
      {["AR5", "AR6"].map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={cn(
            "rounded px-2.5 py-1 text-small transition-colors",
            value === option
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:text-foreground",
          )}
        >
          {option}
        </button>
      ))}
    </div>
  );
}
