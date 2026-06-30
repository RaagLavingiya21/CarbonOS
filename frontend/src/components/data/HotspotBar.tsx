import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type EmissionTier = "low" | "medium" | "high";

/** Share thresholds for the emission-tier color of a single contributor. */
export function shareTier(sharePct: number): EmissionTier {
  if (sharePct >= 40) return "high";
  if (sharePct >= 15) return "medium";
  return "low";
}

const FILL: Record<EmissionTier, string> = {
  low: "bg-data-low",
  medium: "bg-data-medium",
  high: "bg-data-high",
};

/**
 * One contributor's share as a horizontal bar. Color encodes the emission tier;
 * the largest contributor (a hotspot) reads instantly. Hover shows the exact value.
 */
export function HotspotBar({
  label,
  sublabel,
  sharePct,
  value,
  emphasized = false,
}: {
  label: string;
  sublabel?: string;
  sharePct: number;
  value: string;
  emphasized?: boolean;
}) {
  const tier = shareTier(sharePct);
  const width = Math.max(2, Math.min(100, sharePct));

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between gap-3 text-small">
        <span className={cn("min-w-0 truncate", emphasized && "font-medium")}>
          {label}
          {sublabel ? <span className="text-muted-foreground"> · {sublabel}</span> : null}
        </span>
        <span className="shrink-0 tabular-nums text-muted-foreground">
          {value} <span className="text-caption">({sharePct.toFixed(1)}%)</span>
        </span>
      </div>
      <Tooltip content={`${value} — ${sharePct.toFixed(1)}% of total`} side="bottom">
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full transition-[width] duration-panel ease-out", FILL[tier])}
            style={{ width: `${width}%` }}
          />
        </div>
      </Tooltip>
    </div>
  );
}
