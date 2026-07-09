"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Plus, TrendingUp, Target as TargetIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { scope2Api, type Target } from "@/lib/scope2-api";

import { CreateTargetDialog } from "./CreateTargetDialog";
import { TargetProgressCard } from "./TargetProgressCard";

export default function Scope2TargetsPage() {
  const [targets, setTargets] = useState<Target[] | null>(null);
  const [activeTarget, setActiveTarget] = useState<Target | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  const loadTargets = useCallback(async () => {
    try {
      setError(null);
      const [allTargets, active] = await Promise.all([
        scope2Api.listTargets(),
        scope2Api.getActiveTarget(),
      ]);
      setTargets(allTargets);
      setActiveTarget(active);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load targets");
    }
  }, []);

  useEffect(() => {
    loadTargets();
  }, [loadTargets]);

  const handleTargetCreated = () => {
    setShowCreateDialog(false);
    loadTargets();
  };

  if (error) {
    return (
      <div className="container py-8">
        <div className="mb-6">
          <Link href="/scope-2" className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-4 w-4" />
            Back to Scope 2
          </Link>
        </div>
        <ErrorState title="Error loading targets" message={error} />
      </div>
    );
  }

  return (
    <div className="container py-8">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/scope-2" className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-4 w-4" />
            Back to Scope 2
          </Link>
          <div>
            <h1 className="text-3xl font-bold">Reduction Targets</h1>
            <p className="text-gray-600">SBTi-style emissions reduction trajectories</p>
          </div>
        </div>
        <Button onClick={() => setShowCreateDialog(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          New Target
        </Button>
      </div>

      {targets === null ? (
        <div className="space-y-6">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      ) : targets.length === 0 ? (
        <EmptyState
          icon={TargetIcon}
          title="No targets yet"
          description="Set a reduction target to track progress toward your emissions goals."
          action={
            <Button onClick={() => setShowCreateDialog(true)} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Target
            </Button>
          }
        />
      ) : (
        <div className="space-y-6">
          {activeTarget && (
            <Card className="border-2 border-blue-200 bg-blue-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-blue-600" />
                  Active Target
                </CardTitle>
                <CardDescription>Currently tracking your progress</CardDescription>
              </CardHeader>
              <CardContent>
                <TargetProgressCard target={activeTarget} />
              </CardContent>
            </Card>
          )}

          {targets.length > 1 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold">Other Targets</h2>
              <div className="grid gap-4">
                {targets.filter((t) => t.target_id !== activeTarget?.target_id).map((target) => (
                  <Card key={target.target_id}>
                    <CardContent className="pt-6">
                      <TargetProgressCard target={target} />
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <CreateTargetDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} onSuccess={handleTargetCreated} />
    </div>
  );
}
