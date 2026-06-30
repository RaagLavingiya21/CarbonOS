import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

/**
 * A single headline metric — big tabular number + unit, with optional context/source.
 */
export function MetricCard({
  label,
  value,
  unit,
  hint,
  footer,
  className,
}: {
  label: string;
  value: string | number;
  unit?: string;
  hint?: string;
  footer?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("flex flex-col gap-1 p-4", className)}>
      <span className="text-caption font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <span className="flex items-baseline gap-1.5">
        <span className="tabular-nums text-h2 font-semibold leading-none">{value}</span>
        {unit ? <span className="text-small text-muted-foreground">{unit}</span> : null}
      </span>
      {hint ? <span className="text-caption text-muted-foreground">{hint}</span> : null}
      {footer ? <div className="mt-1">{footer}</div> : null}
    </Card>
  );
}
