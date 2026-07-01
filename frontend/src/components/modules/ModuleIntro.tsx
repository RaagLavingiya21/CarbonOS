"use client";

import { useEffect, useState } from "react";
import { HelpCircle, X, type LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

interface ModuleIntroProps {
  moduleKey: string;
  icon: LucideIcon;
  title: string;
  job: string;
  steps: [string, string, string];
  needs?: string;
}

export function ModuleIntro({
  moduleKey,
  icon: Icon,
  title,
  job,
  steps,
  needs,
}: ModuleIntroProps) {
  const storageKey = `module-intro-dismissed:${moduleKey}`;
  const [mounted, setMounted] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    try {
      setDismissed(window.localStorage.getItem(storageKey) === "true");
    } catch {
      // localStorage unavailable — keep the intro expanded.
    }
    setMounted(true);
  }, [storageKey]);

  function setDismissedState(next: boolean) {
    setDismissed(next);
    try {
      window.localStorage.setItem(storageKey, next ? "true" : "false");
    } catch {
      // Ignore persistence failures.
    }
  }

  // Avoid hydration mismatch: render a stable placeholder until mounted.
  if (!mounted) {
    return <div className="h-[52px] rounded-lg border bg-card" aria-hidden />;
  }

  if (dismissed) {
    return (
      <div className="flex items-center gap-3 rounded-lg border bg-card px-3 py-2 shadow-xs">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
          <Icon className="h-4 w-4" aria-hidden />
        </span>
        <p className="text-small font-medium">{title}</p>
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto h-7 w-7"
          aria-label="Show intro"
          onClick={() => setDismissedState(false)}
        >
          <HelpCircle className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    );
  }

  return (
    <div className="relative rounded-lg border bg-card p-4 shadow-xs md:p-5">
      <Button
        variant="ghost"
        size="icon"
        className="absolute right-2 top-2 h-7 w-7 text-muted-foreground"
        aria-label="Dismiss intro"
        onClick={() => setDismissedState(true)}
      >
        <X className="h-4 w-4" aria-hidden />
      </Button>

      <div className="flex items-start gap-3 pr-8">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
          <Icon className="h-5 w-5" aria-hidden />
        </span>
        <div>
          <h3 className="text-h3">{title}</h3>
          <p className="text-small text-muted-foreground">{job}</p>
        </div>
      </div>

      <ol className="mt-4 grid gap-3 sm:grid-cols-3">
        {steps.map((step, index) => (
          <li key={index} className="flex items-start gap-2">
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary text-caption font-medium text-secondary-foreground tabular-nums">
              {index + 1}
            </span>
            <span className="text-small text-muted-foreground">{step}</span>
          </li>
        ))}
      </ol>

      {needs ? (
        <p className="mt-4 text-caption text-muted-foreground">
          <span className="font-medium">What you&apos;ll need:</span> {needs}
        </p>
      ) : null}
    </div>
  );
}
