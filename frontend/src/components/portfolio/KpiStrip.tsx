import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Placeholder } from "@/components/portfolio/Placeholder";

export type KpiTileData = {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: ReactNode;
  /** 0..1 — renders a thin progress bar (e.g. primary-data share). */
  bar?: number;
  /** Tone of the bar. */
  barTone?: "primary" | "success" | "warning";
  /**
   * Period-over-period delta. `undefined` renders an honest "no trend yet"
   * placeholder rather than an invented number.
   */
  deltaPct?: number;
  positiveIsGood?: boolean;
};

/**
 * Dense KPI strip — a single hairline-divided container (Linear/Stripe style),
 * fed by real portfolio aggregates. Unbacked trend/delta slots show placeholders.
 */
export function KpiStrip({ tiles }: { tiles: KpiTileData[] }) {
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-border bg-border lg:grid-cols-4">
      {tiles.map((tile) => (
        <KpiTile key={tile.label} {...tile} />
      ))}
    </div>
  );
}

function KpiTile({
  label,
  value,
  unit,
  hint,
  bar,
  barTone = "primary",
  deltaPct,
  positiveIsGood,
}: KpiTileData) {
  const hasDelta = typeof deltaPct === "number";
  const isGood = hasDelta
    ? positiveIsGood
      ? deltaPct! > 0
      : deltaPct! < 0
    : false;
  const barColor =
    barTone === "success"
      ? "bg-data-low"
      : barTone === "warning"
        ? "bg-data-medium"
        : "bg-primary";

  return (
    <div className="bg-surface p-3">
      <div className="flex items-center justify-between">
        <span className="text-caption font-medium text-muted-foreground">{label}</span>
        {hasDelta ? (
          <span
            className={cn(
              "num inline-flex items-center gap-0.5 rounded px-1 py-0.5 text-caption font-medium",
              isGood ? "bg-data-low-bg text-data-low" : "bg-data-high-bg text-data-high",
            )}
          >
            {deltaPct! < 0 ? "▾" : "▴"}
            {Math.abs(deltaPct!)}%
          </span>
        ) : (
          <span className="text-caption text-muted-foreground/50" title="No trend data yet">
            vs. prior <Placeholder />
          </span>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="num text-[1.5rem] font-semibold leading-none tracking-tight text-foreground">
          {value}
        </span>
        {unit ? <span className="text-small text-muted-foreground">{unit}</span> : null}
      </div>
      {typeof bar === "number" ? (
        <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full", barColor)}
            style={{ width: `${Math.max(0, Math.min(1, bar)) * 100}%` }}
          />
        </div>
      ) : hint ? (
        <div className="mt-1.5 text-caption text-muted-foreground">{hint}</div>
      ) : null}
    </div>
  );
}
