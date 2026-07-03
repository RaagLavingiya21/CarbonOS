"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Trash2 } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EFOverride, api } from "@/lib/api";

export default function FactorMappingsPage() {
  const [overrides, setOverrides] = useState<EFOverride[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadOverrides = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listEFOverrides();
      setOverrides(rows);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOverrides();
  }, [loadOverrides]);

  async function handleDelete(overrideId: number) {
    setDeletingId(overrideId);
    setError(null);
    try {
      await api.deleteEFOverride(overrideId);
      setOverrides((rows) => rows.filter((row) => row.override_id !== overrideId));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button asChild size="sm" variant="outline">
          <Link href="/settings/org">
            <ArrowLeft className="h-4 w-4" />
            Settings
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Factor mappings</h1>
          <p className="text-sm text-muted-foreground">
            Org-wide material → sector overrides applied automatically on future BOM imports.
          </p>
        </div>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Saved overrides</CardTitle>
          <CardDescription>
            Create overrides from a product detail page via Re-map → &quot;Save this mapping for our
            org&quot;.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading mappings...</p>
          ) : overrides.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No saved factor mappings yet. Re-map a low-confidence line item and tick &quot;Save
              for our org&quot; to add one.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="bg-secondary text-muted-foreground">
                  <tr>
                    <th className="px-4 py-3">Material</th>
                    <th className="px-4 py-3">Sector</th>
                    <th className="px-4 py-3">Code</th>
                    <th className="px-4 py-3">Scope</th>
                    <th className="px-4 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {overrides.map((row) => (
                    <tr key={row.override_id} className="border-t bg-card">
                      <td className="px-4 py-3 font-medium">{row.material_normalized}</td>
                      <td className="px-4 py-3">{row.sector_name ?? "—"}</td>
                      <td className="px-4 py-3">
                        <Badge variant="secondary">{row.sector_code}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        {row.org_id ? "Organization" : "Personal"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          disabled={deletingId === row.override_id}
                          onClick={() => void handleDelete(row.override_id)}
                          size="sm"
                          type="button"
                          variant="outline"
                        >
                          <Trash2 className="h-4 w-4" />
                          {deletingId === row.override_id ? "Deleting..." : "Delete"}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
