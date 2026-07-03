import type { ReactNode } from "react";
import { ArrowUpDown } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Primitives for the dense, grouped-header data tables used across the
 * portfolio and product-detail screens. A CSS grid template is shared between
 * the grouped header, the column header, and every row so columns stay aligned.
 * The first column is sticky for horizontal scrolling.
 */

export function GroupHead({
  label,
  span = 1,
  align,
  sticky,
}: {
  label: string;
  span?: number;
  align?: "right";
  sticky?: boolean;
}) {
  return (
    <div
      className={cn(
        "px-3 py-1.5",
        span > 1 && "border-l border-border/60",
        align === "right" && "text-right",
        sticky && "sticky left-0 z-10 bg-surface-2",
      )}
      style={span > 1 ? { gridColumn: `span ${span} / span ${span}` } : undefined}
    >
      {label}
    </div>
  );
}

export function HeadCell({
  children,
  align,
  sticky,
}: {
  children: ReactNode;
  align?: "right";
  sticky?: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center px-3 py-2",
        align === "right" && "justify-end text-right",
        sticky
          ? "sticky left-0 z-10 border-r border-border/60 bg-surface-2"
          : "border-l border-border/30",
      )}
    >
      {children}
    </div>
  );
}

export function Cell({
  children,
  align,
  sticky,
  className,
}: {
  children: ReactNode;
  align?: "right";
  sticky?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex items-center px-3 py-2",
        align === "right" && "justify-end text-right",
        sticky
          ? "sticky left-0 z-[5] border-r border-border/60 bg-surface group-hover:bg-muted/60"
          : "border-l border-border/30",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function SortHead({ label, numeric }: { label: string; numeric?: boolean }) {
  return (
    <button
      type="button"
      className={cn("inline-flex items-center gap-1 hover:text-foreground", numeric && "justify-end")}
    >
      {label}
      <ArrowUpDown className="h-2.5 w-2.5 opacity-50" />
    </button>
  );
}

/** Thin progress bar with a right-aligned percent label (e.g. primary-data share). */
export function PctBar({ value, className }: { value: number; className?: string }) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div className={cn("flex w-full items-center gap-2", className)}>
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="absolute inset-y-0 left-0 bg-primary"
          style={{ width: `${pct * 100}%` }}
        />
      </div>
      <span className="num w-8 shrink-0 text-right text-caption font-medium text-foreground">
        {(pct * 100).toFixed(0)}%
      </span>
    </div>
  );
}
