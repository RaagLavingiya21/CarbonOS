"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Boxes, Layers } from "lucide-react";

import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { InventoryVersion, scope3Api } from "@/lib/scope3-api";
import { formatKg } from "@/lib/utils";

const ENTRIES = [
  {
    href: "/scope-3/inventory",
    icon: Layers,
    title: "Corporate Scope 3 inventory",
    body: "Create a reporting-year inventory, import GL/ERP spend, and calculate a 15-category, spend-based Scope 3 footprint.",
  },
];

export default function Scope3Page() {
  const [inventories, setInventories] = useState<InventoryVersion[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    scope3Api
      .listInventories()
      .then(setInventories)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load."));
  }, []);

  const loading = !error && inventories === null;
  const latest = inventories?.[0];

  return (
    <div className="space-y-8 p-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Scope 3</h1>
        <p className="text-muted-foreground mt-1 max-w-2xl text-sm">
          Corporate value-chain emissions. Screening-grade, spend-based (Open CEDA 2025),
          GHG-Protocol-conformant across all 15 categories.
        </p>
      </header>

      {error && <ErrorState message={error} />}

      {loading ? (
        <Skeleton className="h-24 w-full" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader>
              <CardDescription className="flex items-center gap-2">
                <Boxes className="h-4 w-4" /> Inventories
              </CardDescription>
              <CardTitle className="text-3xl">{inventories?.length ?? 0}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Latest reporting year</CardDescription>
              <CardTitle className="text-3xl">{latest?.reporting_year ?? "—"}</CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardDescription>Latest total</CardDescription>
              <CardTitle className="text-3xl">
                {latest?.total_kg_co2e != null ? formatKg(latest.total_kg_co2e) : "—"}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {ENTRIES.map((e) => (
          <Link key={e.href} href={e.href}>
            <Card className="hover:border-primary/50 h-full transition-colors">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <e.icon className="h-5 w-5" /> {e.title}
                  <ArrowRight className="text-muted-foreground ml-auto h-4 w-4" />
                </CardTitle>
                <CardDescription>{e.body}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
