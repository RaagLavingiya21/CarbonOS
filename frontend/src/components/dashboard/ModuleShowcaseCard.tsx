"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface ModuleShowcaseData {
  /** Module display name. */
  name: string;
  /** Decorative icon for the module. */
  icon: LucideIcon;
  /** One-line "job it does". */
  job: string;
  /** The problem the module solves. */
  problem: string;
  /** Three-step "how it works". */
  steps: [string, string, string];
  /** Label for the CTA button. */
  ctaLabel: string;
  /** Chat message the CTA navigates with. */
  message: string;
}

/**
 * A large, static showcase tile for a module — everything (problem,
 * how-it-works, CTA) is visible at once, no hover/flip interaction needed.
 */
export function ModuleShowcaseCard({
  name,
  icon: Icon,
  job,
  problem,
  steps,
  ctaLabel,
  message,
}: ModuleShowcaseData) {
  const router = useRouter();

  const handleNavigate = useCallback(() => {
    router.push(`/chat?message=${encodeURIComponent(message)}`);
  }, [router, message]);

  return (
    <div className="flex h-full flex-col gap-4 rounded-lg border bg-card p-6 shadow-xs md:p-8">
      <span
        aria-hidden
        className="flex h-12 w-12 items-center justify-center rounded-lg bg-secondary text-primary"
      >
        <Icon className="h-6 w-6" />
      </span>

      <div className="space-y-1.5">
        <h3 className="text-h2 leading-tight">{name}</h3>
        <p className="text-body text-muted-foreground text-pretty">{job}</p>
      </div>

      <p className="text-small text-foreground/90 text-pretty">{problem}</p>

      <ol className="flex flex-col gap-2">
        {steps.map((step, index) => (
          <li
            key={step}
            className="flex items-start gap-2.5 text-small text-muted-foreground"
          >
            <span
              aria-hidden
              className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-secondary text-caption font-medium tabular-nums text-secondary-foreground"
            >
              {index + 1}
            </span>
            <span className="text-pretty">{step}</span>
          </li>
        ))}
      </ol>

      <Button
        type="button"
        className="mt-auto w-full"
        onClick={handleNavigate}
        aria-label={`${ctaLabel} — ${name}`}
      >
        {ctaLabel}
        <ArrowRight className="h-3.5 w-3.5" aria-hidden />
      </Button>
    </div>
  );
}
