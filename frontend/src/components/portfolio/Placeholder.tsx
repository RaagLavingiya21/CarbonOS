import { cn } from "@/lib/utils";

/**
 * Honest placeholder for values the current API does not yet provide
 * (e.g. period-over-period delta, per-row confidence, hotspot mix).
 * Renders a muted dash with a "no data yet" tooltip — never an invented number.
 */
export function Placeholder({
  label = "No data yet",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <span
      title={label}
      aria-label={label}
      className={cn("select-none text-muted-foreground/50", className)}
    >
      —
    </span>
  );
}
