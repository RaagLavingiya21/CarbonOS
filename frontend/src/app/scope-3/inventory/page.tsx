"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, FileUp, Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  InventoryVersion,
  scope3Api,
  BOUNDARY_APPROACHES,
} from "@/lib/scope3-api";
import { formatKg } from "@/lib/utils";

export default function InventoryPage() {
  const router = useRouter();
  const [inventories, setInventories] = useState<InventoryVersion[] | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [importingId, setImportingId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [formData, setFormData] = useState({
    reportingYear: new Date().getFullYear(),
    boundaryApproach: "operational_control",
  });

  const loadInventories = async () => {
    try {
      const data = await scope3Api.listInventories();
      setInventories(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load inventories.");
      setInventories([]);
    }
  };

  useEffect(() => {
    loadInventories();
  }, []);

  const handleCreateInventory = async () => {
    setCreating(true);
    try {
      const newInventory = await scope3Api.createInventory({
        reporting_year: parseInt(formData.reportingYear.toString()),
        boundary_approach: formData.boundaryApproach,
      });
      setShowCreateForm(false);
      setFormData({
        reportingYear: new Date().getFullYear(),
        boundaryApproach: "operational_control",
      });
      await loadInventories();
      router.push(`/scope-3/inventory/${newInventory.inventory_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create inventory.");
    } finally {
      setCreating(false);
    }
  };

  const handleFileSelected = async (
    inventoryId: number,
    file: File,
  ) => {
    setImporting(true);
    setImportingId(inventoryId);
    try {
      await scope3Api.importSpend(inventoryId, file);
      await loadInventories();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to import spend file.");
    } finally {
      setImporting(false);
      setImportingId(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleImportClick = (inventoryId: number) => {
    setImportingId(inventoryId);
    fileInputRef.current?.click();
  };

  const handleLockInventory = async (inventoryId: number) => {
    try {
      await scope3Api.lock(inventoryId);
      await loadInventories();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to lock inventory.");
    }
  };

  const loading = inventories === null && !error;

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Inventories</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Create, import, and manage Scope 3 inventories.
          </p>
        </div>
      </div>

      {!showCreateForm ? (
        <Button className="mb-6 gap-2" onClick={() => setShowCreateForm(true)}>
          <FileUp className="h-4 w-4" />
          New Inventory
        </Button>
      ) : (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Create Inventory</CardTitle>
            <CardDescription>
              Start a new Scope 3 spend-based inventory for a reporting year.
            </CardDescription>
          </CardHeader>
          <div className="px-6 pb-6 space-y-4">
            <div>
              <Label htmlFor="reporting-year">Reporting Year</Label>
              <Input
                id="reporting-year"
                type="number"
                min="2000"
                max="2099"
                value={formData.reportingYear}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    reportingYear: parseInt(e.target.value),
                  })
                }
              />
            </div>
            <div>
              <Label htmlFor="boundary">Boundary Approach</Label>
              <Select
                value={formData.boundaryApproach}
                onValueChange={(value) =>
                  setFormData({ ...formData, boundaryApproach: value })
                }
              >
                <SelectTrigger id="boundary">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BOUNDARY_APPROACHES.map((approach) => (
                    <SelectItem key={approach} value={approach}>
                      {approach.replace(/_/g, " ").replace(/^\w/, (c) =>
                        c.toUpperCase(),
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setShowCreateForm(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreateInventory}
                disabled={creating}
              >
                {creating ? "Creating..." : "Create"}
              </Button>
            </div>
          </div>
        </Card>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={(e) => {
          const file = e.currentTarget.files?.[0];
          if (file && importingId) {
            handleFileSelected(importingId, file);
          }
        }}
      />

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-[300px] w-full rounded-lg" />
        </div>
      ) : inventories && inventories.length > 0 ? (
        <div className="space-y-4">
          {inventories.map((inv) => (
            <Card key={inv.inventory_id}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">
                      {inv.reporting_year} Inventory
                    </CardTitle>
                    <CardDescription className="capitalize">
                      {inv.boundary_approach.replace(/_/g, " ")} boundary
                    </CardDescription>
                  </div>
                  <span
                    className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                      inv.status === "locked"
                        ? "bg-green-100 text-green-800"
                        : inv.status === "calculated"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-800"
                    }`}
                  >
                    {inv.status}
                  </span>
                </div>
              </CardHeader>
              <div className="border-t px-6 py-3">
                <div className="grid gap-4 sm:grid-cols-3 mb-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Emissions</p>
                    <p className="font-mono font-semibold">
                      {inv.total_kg_co2e !== null
                        ? formatKg(inv.total_kg_co2e)
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Created</p>
                    <p className="font-semibold text-sm">
                      {inv.created_at
                        ? new Date(inv.created_at).toLocaleDateString()
                        : "—"}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Version</p>
                    <p className="font-semibold text-sm">{inv.version}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link href={`/scope-3/inventory/${inv.inventory_id}`}>
                    <Button variant="outline" size="sm">
                      View
                    </Button>
                  </Link>
                  {inv.status !== "locked" && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleImportClick(inv.inventory_id)}
                        disabled={importing && importingId === inv.inventory_id}
                      >
                        <FileUp className="h-3 w-3 mr-1" />
                        {importing && importingId === inv.inventory_id
                          ? "Importing..."
                          : "Import"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleLockInventory(inv.inventory_id)}
                      >
                        <Lock className="h-3 w-3 mr-1" />
                        Lock
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>No Inventories</CardTitle>
            <CardDescription>
              Create your first Scope 3 inventory to get started.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
