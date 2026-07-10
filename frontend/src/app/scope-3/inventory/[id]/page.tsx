"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, BarChart3, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  InventoryDetail,
  scope3Api,
  SCOPE3_CATEGORY_NAMES,
} from "@/lib/scope3-api";
import { formatKg } from "@/lib/utils";

export default function InventoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const inventoryId = parseInt(params.id as string);

  const [detail, setDetail] = useState<InventoryDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [locking, setLocking] = useState(false);

  const loadDetail = async () => {
    try {
      const data = await scope3Api.getInventory(inventoryId);
      setDetail(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load inventory.");
    }
  };

  useEffect(() => {
    loadDetail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inventoryId]);

  const handleCalculate = async () => {
    setCalculating(true);
    try {
      const data = await scope3Api.calculate(inventoryId);
      setDetail(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to calculate.");
    } finally {
      setCalculating(false);
    }
  };

  const handleLock = async () => {
    setLocking(true);
    try {
      const locked = await scope3Api.lock(inventoryId);
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              version: locked,
            }
          : null,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to lock.");
    } finally {
      setLocking(false);
    }
  };

  const loading = detail === null && !error;
  const version = detail?.version;
  const categories = detail?.categories || [];

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <button
          onClick={() => router.back()}
          className="inline-flex"
        >
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {version
              ? `Inventory ${version.inventory_id} (${version.reporting_year})`
              : "Inventory Detail"}
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            {version?.boundary_approach.replace(/_/g, " ")} boundary approach
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-[200px] w-full rounded-lg" />
          <Skeleton className="h-[400px] w-full rounded-lg" />
        </div>
      ) : version ? (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Status</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold capitalize">
                  {version.status}
                </div>
                {version.locked_at && (
                  <p className="text-xs text-muted-foreground">
                    Locked{" "}
                    {new Date(version.locked_at).toLocaleDateString()}
                  </p>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Total Emissions
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatKg(version.total_kg_co2e || 0)}
                </div>
                <p className="text-xs text-muted-foreground">kg CO₂e</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Categories
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {categories.filter((c) => c.total_kg_co2e > 0).length}/15
                </div>
                <p className="text-xs text-muted-foreground">
                  with emissions data
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Base Year
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {version.is_base_year ? "Yes" : "No"}
                </div>
                <p className="text-xs text-muted-foreground">
                  {version.is_base_year
                    ? "Baseline for targets"
                    : "Reporting only"}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card className="mb-6">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Emissions by Category</CardTitle>
                  <CardDescription>
                    GHG Protocol Scope 3 category breakdown.
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  {version.status !== "locked" && (
                    <>
                      <Button
                        onClick={handleCalculate}
                        disabled={calculating}
                        className="gap-2"
                      >
                        <BarChart3 className="h-4 w-4" />
                        {calculating ? "Calculating..." : "Calculate"}
                      </Button>
                      <Button
                        onClick={handleLock}
                        disabled={locking || version.status !== "calculated"}
                        variant="outline"
                        className="gap-2"
                      >
                        <Lock className="h-4 w-4" />
                        {locking ? "Locking..." : "Lock"}
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {categories.length > 0 ? (
                <div className="space-y-2">
                  {categories.map((cat) => (
                    <div
                      key={cat.scope3_category}
                      className="grid grid-cols-1 gap-2 border-b pb-3 last:border-0 sm:grid-cols-5"
                    >
                      <div>
                        <p className="text-xs text-muted-foreground">Category</p>
                        <p className="font-mono text-sm font-semibold">
                          Cat {cat.scope3_category}
                        </p>
                      </div>
                      <div className="sm:col-span-2">
                        <p className="text-xs text-muted-foreground">Name</p>
                        <p className="text-sm">
                          {SCOPE3_CATEGORY_NAMES[cat.scope3_category] ||
                            "Unknown"}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Emissions</p>
                        <p className="font-mono font-semibold">
                          {formatKg(cat.total_kg_co2e)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">
                          Lines / Method
                        </p>
                        <p className="text-sm">
                          {cat.line_count} / {cat.method}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-lg border border-dashed border-border bg-muted/30 px-4 py-8 text-center">
                  <BarChart3 className="mx-auto h-8 w-8 text-muted-foreground" />
                  <p className="mt-2 text-sm text-muted-foreground">
                    No emissions data yet. Import spend records and calculate
                    to populate categories.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <p className="text-xs text-muted-foreground">
            Inventory created{" "}
            {version.created_at
              ? new Date(version.created_at).toLocaleDateString()
              : "recently"}
            . Version {version.version}.
          </p>
        </>
      ) : null}
    </div>
  );
}
