"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, ListChecks } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  scope1Api,
  type S1DataOwner,
  type S1Readiness,
  type S1Source,
} from "@/lib/scope1-api";

import { InventoryPicker, useInventories } from "../_lib";

const STATUSES = ["missing", "requested", "in_progress", "received", "entered", "verified"];

function statusVariant(status: string): "high" | "medium" | "info" | "low" {
  if (status === "missing") return "high";
  if (status === "requested" || status === "in_progress") return "medium";
  if (status === "received") return "info";
  return "low"; // entered | verified
}

export default function Scope1CollectionPage() {
  const { inventories, active, activeId, setActiveId } = useInventories();
  const [sources, setSources] = useState<S1Source[]>([]);
  const [owners, setOwners] = useState<S1DataOwner[]>([]);
  const [readiness, setReadiness] = useState<S1Readiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [src, own] = await Promise.all([scope1Api.listSources(), scope1Api.listDataOwners()]);
      setSources(src);
      setOwners(own);
      setReadiness(activeId ? await scope1Api.readiness(activeId) : null);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [activeId]);

  useEffect(() => {
    void load();
  }, [load]);

  const statusBySource = new Map<string, Record<string, unknown>>();
  readiness?.items.forEach((item) => {
    statusBySource.set(String(item.emission_source_id), item);
  });

  async function initTracking() {
    if (!activeId) return;
    try {
      await scope1Api.initCollection(activeId);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function updateStatus(source: S1Source, patch: { status?: string; data_owner_id?: string }) {
    if (!activeId || !active) return;
    const current = statusBySource.get(source.id);
    try {
      await scope1Api.setCollectionStatus({
        inventory_id: activeId,
        emission_source_id: source.id,
        period_start: active.period_start,
        period_end: active.period_end,
        status: patch.status ?? (current?.status as string) ?? "missing",
        data_owner_id: patch.data_owner_id ?? (current?.data_owner_id as string) ?? null,
      });
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/scope-1">
          <ArrowLeft className="h-4 w-4" />
          Back to Scope 1
        </Link>
      </Button>

      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ListChecks className="h-6 w-6 text-muted-foreground" />
            <h1 className="text-h1">Data collection</h1>
          </div>
          <p className="mt-2 text-small text-muted-foreground">
            Know every source, who owns its data, and what is still missing — before the deadline.
          </p>
        </div>
        <InventoryPicker inventories={inventories} activeId={activeId} onChange={setActiveId} />
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {!activeId ? (
        <Alert>
          <AlertDescription>
            Create an inventory first in{" "}
            <Link href="/scope-1/setup" className="font-medium underline-offset-4 hover:underline">
              Set up inventory
            </Link>
            .
          </AlertDescription>
        </Alert>
      ) : (
        <>
          {readiness ? (
            <Card>
              <CardHeader>
                <CardTitle>Readiness</CardTitle>
                <CardDescription>
                  {readiness.complete} of {readiness.total} source-periods collected
                  {readiness.total === 0 ? " — initialize tracking to begin." : "."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-3">
                  <Progress value={readiness.completeness_pct} className="flex-1" />
                  <span className="text-small font-semibold tabular-nums">
                    {Math.round(readiness.completeness_pct)}%
                  </span>
                </div>
                <Button type="button" variant="outline" onClick={initTracking}>
                  {readiness.total === 0 ? "Initialize tracking" : "Add tracking for new sources"}
                </Button>
              </CardContent>
            </Card>
          ) : null}

          <DataOwnerSection owners={owners} onSaved={load} onError={setError} />

          <Card>
            <CardHeader>
              <CardTitle>Sources</CardTitle>
              <CardDescription>Assign an owner and track collection status per source.</CardDescription>
            </CardHeader>
            <CardContent>
              {sources.length === 0 ? (
                <p className="text-small text-muted-foreground">
                  No sources yet. Register them in Set up inventory.
                </p>
              ) : (
                <div className="overflow-x-auto rounded-lg border">
                  <table className="w-full min-w-[640px] text-left text-sm">
                    <thead className="bg-secondary text-muted-foreground">
                      <tr>
                        <th className="px-3 py-2">Source</th>
                        <th className="px-3 py-2">Owner</th>
                        <th className="px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sources.map((source) => {
                        const row = statusBySource.get(source.id);
                        const status = (row?.status as string) ?? "missing";
                        const ownerId = (row?.data_owner_id as string) ?? "";
                        return (
                          <tr key={source.id} className="border-t bg-card">
                            <td className="px-3 py-2 font-medium">{source.source_name}</td>
                            <td className="px-3 py-2">
                              <select
                                value={ownerId}
                                onChange={(e) => updateStatus(source, { data_owner_id: e.target.value })}
                                className="h-8 rounded-md border bg-card px-2 text-small"
                              >
                                <option value="">Unassigned</option>
                                {owners.map((owner) => (
                                  <option key={owner.id} value={owner.id}>
                                    {owner.name}
                                  </option>
                                ))}
                              </select>
                            </td>
                            <td className="px-3 py-2">
                              <div className="flex items-center gap-2">
                                <Badge variant={statusVariant(status)}>{status.replace(/_/g, " ")}</Badge>
                                <select
                                  value={status}
                                  onChange={(e) => updateStatus(source, { status: e.target.value })}
                                  className="h-8 rounded-md border bg-card px-2 text-small"
                                >
                                  {STATUSES.map((option) => (
                                    <option key={option} value={option}>
                                      {option.replace(/_/g, " ")}
                                    </option>
                                  ))}
                                </select>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function DataOwnerSection({
  owners,
  onSaved,
  onError,
}: {
  owners: S1DataOwner[];
  onSaved: () => void;
  onError: (message: string) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!name.trim()) return;
    setSaving(true);
    try {
      await scope1Api.createDataOwner({
        name: name.trim(),
        email: email.trim() || null,
        role_title: role.trim() || null,
      });
      setName("");
      setEmail("");
      setRole("");
      onSaved();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Data owners</CardTitle>
        <CardDescription>The people who supply each source&apos;s data.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Jordan Lee" />
          </div>
          <div className="space-y-1.5">
            <Label>Email</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="jordan@site.com" />
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Facility manager" />
          </div>
        </div>
        <Button type="button" onClick={submit} disabled={saving || !name.trim()}>
          Add data owner
        </Button>
        {owners.length > 0 ? (
          <ul className="divide-y rounded-lg border">
            {owners.map((owner) => (
              <li key={owner.id} className="flex items-center justify-between px-3 py-2 text-small">
                <span className="font-medium">{owner.name}</span>
                <span className="text-muted-foreground">
                  {owner.role_title ?? ""}
                  {owner.email ? ` · ${owner.email}` : ""}
                </span>
              </li>
            ))}
          </ul>
        ) : null}
      </CardContent>
    </Card>
  );
}
