"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ClipboardList, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  InventoryVersion,
  QuestionnaireRequest,
  scope3Api,
} from "@/lib/scope3-api";

const NO_INVENTORY = "none";

function statusVariant(status: string) {
  if (status === "submitted") return "high" as const;
  if (status === "in_progress") return "info" as const;
  return "neutral" as const;
}

export default function QuestionnairesPage() {
  const router = useRouter();
  const [items, setItems] = useState<QuestionnaireRequest[] | null>(null);
  const [inventories, setInventories] = useState<InventoryVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    customer_name: "",
    framework: "",
    deadline: "",
    inventory_id: NO_INVENTORY,
  });

  const load = async () => {
    try {
      const [reqs, invs] = await Promise.all([
        scope3Api.listQuestionnaires(),
        scope3Api.listInventories().catch(() => [] as InventoryVersion[]),
      ]);
      setItems(reqs);
      setInventories(invs);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load questionnaires.");
      setItems([]);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const created = await scope3Api.createQuestionnaire({
        customer_name: form.customer_name.trim() || null,
        framework: form.framework.trim() || null,
        deadline: form.deadline || null,
        inventory_id:
          form.inventory_id === NO_INVENTORY ? null : Number(form.inventory_id),
      });
      router.push(`/scope-3/questionnaires/${created.request_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to create questionnaire.");
      setCreating(false);
    }
  };

  const loading = items === null && !error;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center gap-3">
        <Link href="/scope-3" className="inline-flex">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Questionnaires</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Answer inbound customer / CDP / EcoVadis requests from your inventory.
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} />
        </div>
      )}

      {!showForm ? (
        <Button className="mb-6 gap-2" onClick={() => setShowForm(true)}>
          <Plus className="h-4 w-4" />
          New questionnaire
        </Button>
      ) : (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>New questionnaire</CardTitle>
            <CardDescription>
              Create the request, then upload the questionnaire file to auto-detect the
              framework and questions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label htmlFor="customer">Customer name</Label>
                <Input
                  id="customer"
                  value={form.customer_name}
                  onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="framework">Framework (optional)</Label>
                <Input
                  id="framework"
                  placeholder="Auto-detected on upload"
                  value={form.framework}
                  onChange={(e) => setForm({ ...form, framework: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="deadline">Deadline</Label>
                <Input
                  id="deadline"
                  type="date"
                  value={form.deadline}
                  onChange={(e) => setForm({ ...form, deadline: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="inventory">Answer from inventory</Label>
                <Select
                  value={form.inventory_id}
                  onValueChange={(v) => setForm({ ...form, inventory_id: v })}
                >
                  <SelectTrigger id="inventory">
                    <SelectValue placeholder="Attach later" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={NO_INVENTORY}>Attach later</SelectItem>
                    {inventories.map((inv) => (
                      <SelectItem
                        key={inv.inventory_id}
                        value={String(inv.inventory_id)}
                      >
                        {inv.reporting_year} · {inv.status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                onClick={() => setShowForm(false)}
                disabled={creating}
              >
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? "Creating..." : "Create"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <Skeleton className="h-[240px] w-full rounded-lg" />
      ) : items && items.length > 0 ? (
        <div className="space-y-3">
          {items.map((q) => (
            <Link
              key={q.request_id}
              href={`/scope-3/questionnaires/${q.request_id}`}
              className="block"
            >
              <Card className="hover:border-primary/50 transition-colors">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle className="text-base">
                        {q.customer_name || "Untitled request"}
                      </CardTitle>
                      <CardDescription className="uppercase">
                        {q.framework}
                        {q.deadline ? ` · due ${q.deadline}` : ""}
                      </CardDescription>
                    </div>
                    <Badge variant={statusVariant(q.status)} className="capitalize">
                      {q.status.replace(/_/g, " ")}
                    </Badge>
                  </div>
                </CardHeader>
              </Card>
            </Link>
          ))}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ClipboardList className="h-5 w-5" /> No questionnaires yet
            </CardTitle>
            <CardDescription>
              Create one to answer an inbound customer request.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
