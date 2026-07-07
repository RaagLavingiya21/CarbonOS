"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Circle, Rocket } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { scope1Api, type S1Onboarding } from "@/lib/scope1-api";

/**
 * Guided-setup checklist. Backend-driven: each step reflects real org state
 * (`GET /api/scope1/onboarding`), so it stays honest as data arrives and
 * self-hides once setup is complete.
 */
export function OnboardingChecklist() {
  const [data, setData] = useState<S1Onboarding | null>(null);
  const [dismissed, setDismissed] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await scope1Api.onboarding());
    } catch {
      setData(null); // non-fatal: the dashboard still works without the wizard
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (!data || data.total === 0) return null;

  const complete = data.complete === data.total;
  if (complete && dismissed) return null;

  return (
    <Card className={complete ? "border-emerald-500/40" : "border-primary/40"}>
      <CardHeader className="flex flex-row items-start justify-between gap-4 space-y-0">
        <div className="flex items-center gap-2">
          <Rocket className="h-5 w-5 text-primary" />
          <CardTitle>{complete ? "You're all set" : "Get set up"}</CardTitle>
        </div>
        <div className="min-w-[8rem] text-right">
          <p className="text-small text-muted-foreground">
            {data.complete} of {data.total} done
          </p>
          <Progress value={data.pct} className="mt-1" />
        </div>
      </CardHeader>
      <CardContent className="space-y-1">
        {data.steps.map((step) => {
          const isNext = !complete && step.key === data.next_key;
          return (
            <div
              key={step.key}
              className={`flex items-center gap-3 rounded-md px-2 py-2 ${
                isNext ? "bg-primary/5" : ""
              }`}
            >
              {step.done ? (
                <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
              ) : (
                <Circle className="h-5 w-5 shrink-0 text-muted-foreground" />
              )}
              <div className="min-w-0 flex-1">
                <p
                  className={`text-small font-medium ${
                    step.done ? "text-muted-foreground line-through" : ""
                  }`}
                >
                  {step.title}
                  {step.done && step.count > 0 ? (
                    <span className="ml-2 font-normal text-muted-foreground no-underline">
                      ({step.count})
                    </span>
                  ) : null}
                </p>
                {!step.done ? (
                  <p className="text-caption text-muted-foreground">{step.description}</p>
                ) : null}
              </div>
              {isNext ? (
                <Button asChild size="sm">
                  <Link href={step.href}>
                    {step.cta}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              ) : !step.done ? (
                <Button asChild size="sm" variant="ghost">
                  <Link href={step.href}>{step.cta}</Link>
                </Button>
              ) : null}
            </div>
          );
        })}
        {complete ? (
          <div className="flex justify-end pt-2">
            <Button size="sm" variant="ghost" onClick={() => setDismissed(true)}>
              Dismiss
            </Button>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
