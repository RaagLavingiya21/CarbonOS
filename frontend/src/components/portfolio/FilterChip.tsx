"use client";

import Link from "next/link";

import { cn } from "@/lib/utils";

/**
 * Compact filter chip: quiet "label" + emphasized "value". Renders as a link
 * when `href` is given (so filters stay URL-driven), else a button.
 */
export function FilterChip({
  label,
  value,
  active,
  href,
  onClick,
}: {
  label: string;
  value: string;
  active?: boolean;
  href?: string;
  onClick?: () => void;
}) {
  const className = cn(
    "flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-small shadow-xs transition-colors duration-micro",
    active
      ? "border-primary/30 bg-primary/10 text-primary"
      : "border-border bg-surface text-foreground hover:bg-muted",
  );
  const inner = (
    <>
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </>
  );
  if (href) {
    return (
      <Link href={href} className={className}>
        {inner}
      </Link>
    );
  }
  return (
    <button type="button" onClick={onClick} className={className}>
      {inner}
    </button>
  );
}

/**
 * Small segmented control for view switching (Table / Board / Chart).
 * Disabled segments still render — they mark planned views without faking them.
 */
export function SegmentedControl({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string; disabled?: boolean }[];
  value: string;
  onChange?: (value: string) => void;
}) {
  return (
    <div className="flex items-center rounded-md border border-border bg-surface p-0.5 text-caption shadow-xs">
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            disabled={opt.disabled}
            title={opt.disabled ? "Coming soon" : undefined}
            onClick={() => onChange?.(opt.value)}
            className={cn(
              "rounded px-2 py-0.5 transition-colors duration-micro",
              active
                ? "bg-muted font-medium text-foreground"
                : "text-muted-foreground hover:text-foreground",
              opt.disabled && "cursor-not-allowed opacity-40 hover:text-muted-foreground",
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
