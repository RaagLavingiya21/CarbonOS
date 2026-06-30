"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export interface ModuleFlipCardData {
  /** Module display name shown on the front. */
  name: string;
  /** Decorative icon for the module. */
  icon: LucideIcon;
  /** One-line "job it does" shown on the front. */
  job: string;
  /** The problem the module solves, shown on the back. */
  problem: string;
  /** Three-step "how it works", shown on the back. */
  steps: [string, string, string];
  /** Label for the CTA button on the back. */
  ctaLabel: string;
  /** Chat message the CTA navigates with. */
  message: string;
}

export function ModuleFlipCard({
  name,
  icon: Icon,
  job,
  problem,
  steps,
  ctaLabel,
  message,
}: ModuleFlipCardData) {
  const router = useRouter();
  const [flipped, setFlipped] = useState(false);

  const handleNavigate = useCallback(() => {
    router.push(`/chat?message=${encodeURIComponent(message)}`);
  }, [router, message]);

  return (
    <div
      // `group` drives hover/focus flip; `flipped` state drives touch tap-flip.
      data-flipped={flipped ? "" : undefined}
      className="group relative h-full [perspective:1200px]"
    >
      {/* Inner wrapper that rotates. In reduced-motion mode we don't rotate;
          the two faces cross-fade via opacity instead (handled per-face). */}
      <div
        className={
          "relative min-h-[200px] w-full rounded-lg transition-transform duration-panel ease-out [transform-style:preserve-3d] " +
          "group-hover:[transform:rotateY(180deg)] group-focus-within:[transform:rotateY(180deg)] " +
          "data-[flipped]:[transform:rotateY(180deg)] " +
          "motion-reduce:transition-none motion-reduce:transform-none " +
          "motion-reduce:group-hover:transform-none motion-reduce:group-focus-within:transform-none " +
          "motion-reduce:data-[flipped]:transform-none"
        }
      >
        {/* ── FRONT ──────────────────────────────────────────────── */}
        <button
          type="button"
          // Tap toggles the back for touch; hover/focus handle pointer + keyboard.
          onClick={() => setFlipped((value) => !value)}
          aria-label={`${name}. ${job} Activate to reveal details.`}
          className={
            "absolute inset-0 flex h-full w-full flex-col items-start gap-3 rounded-lg border bg-card p-5 text-left shadow-xs [backface-visibility:hidden] " +
            "transition-opacity duration-panel ease-out " +
            "outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background " +
            // Reduced motion: cross-fade — front fades out when flipped.
            "motion-reduce:[backface-visibility:visible] " +
            "motion-reduce:group-hover:opacity-0 motion-reduce:group-focus-within:opacity-0 " +
            "motion-reduce:data-[flipped]:opacity-0 group-data-[flipped]:motion-reduce:opacity-0"
          }
        >
          <span
            aria-hidden
            className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary text-primary"
          >
            <Icon className="h-5 w-5" />
          </span>
          <h3 className="text-h3 leading-tight">{name}</h3>
          <p className="text-small text-muted-foreground text-pretty">{job}</p>
        </button>

        {/* ── BACK ───────────────────────────────────────────────── */}
        <div
          className={
            "absolute inset-0 flex h-full w-full flex-col gap-3 rounded-lg border bg-card p-5 shadow-xs [backface-visibility:hidden] [transform:rotateY(180deg)] " +
            "transition-opacity duration-panel ease-out " +
            // Default (animated): back hidden until rotation reveals it; pointer
            // events only when revealed so the CTA isn't clickable while hidden.
            "pointer-events-none opacity-0 " +
            "group-hover:pointer-events-auto group-hover:opacity-100 " +
            "group-focus-within:pointer-events-auto group-focus-within:opacity-100 " +
            "group-data-[flipped]:pointer-events-auto group-data-[flipped]:opacity-100 " +
            // Reduced motion: no rotation, cross-fade in.
            "motion-reduce:[backface-visibility:visible] motion-reduce:[transform:none]"
          }
        >
          <p className="text-small text-foreground text-pretty">{problem}</p>
          <ol className="flex flex-1 flex-col gap-1.5">
            {steps.map((step, index) => (
              <li
                key={step}
                className="flex items-start gap-2 text-caption text-muted-foreground"
              >
                <span
                  aria-hidden
                  className="mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-secondary text-[0.625rem] font-medium tabular-nums text-secondary-foreground"
                >
                  {index + 1}
                </span>
                <span className="text-pretty">{step}</span>
              </li>
            ))}
          </ol>
          <Button
            type="button"
            size="sm"
            onClick={handleNavigate}
            aria-label={`${ctaLabel} — ${name}`}
            className="w-full"
          >
            {ctaLabel}
            <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Button>
        </div>
      </div>
    </div>
  );
}
