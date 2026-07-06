import {
  CheckCircle2,
  Circle,
  CircleDot,
  Clock,
  FileCheck2,
  Flag,
  type LucideIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Lifecycle status chip. Maps the real `status` field on an analysis to a
 * compact icon + tinted label, using the semantic data palette.
 */
type StatusKey =
  | "draft"
  | "calculated"
  | "under_review"
  | "approved"
  | "published"
  | "flagged"
  | "saved";

const STATUS_META: Record<
  StatusKey,
  { label: string; Icon: LucideIcon; className: string }
> = {
  draft: { label: "Draft", Icon: Circle, className: "bg-muted text-muted-foreground" },
  calculated: {
    label: "Calculated",
    Icon: CircleDot,
    className: "bg-data-info-bg text-data-info",
  },
  under_review: {
    label: "Review",
    Icon: Clock,
    className: "bg-data-medium-bg text-data-medium",
  },
  approved: {
    label: "Approved",
    Icon: CheckCircle2,
    className: "bg-data-low-bg text-data-low",
  },
  published: {
    label: "Published",
    Icon: FileCheck2,
    className: "bg-primary/10 text-primary ring-1 ring-primary/20",
  },
  flagged: {
    label: "Flagged",
    Icon: Flag,
    className: "bg-data-high-bg text-data-high",
  },
  saved: { label: "Saved", Icon: CircleDot, className: "bg-muted text-muted-foreground" },
};

function resolveStatus(status?: string | null): StatusKey {
  const key = (status ?? "saved").toLowerCase().replace(/\s+/g, "_");
  return (key in STATUS_META ? key : "saved") as StatusKey;
}

export function StatusChip({
  status,
  className,
}: {
  status?: string | null;
  className?: string;
}) {
  const meta = STATUS_META[resolveStatus(status)];
  const Icon = meta.Icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-caption font-medium",
        meta.className,
        className,
      )}
    >
      <Icon className="h-2.5 w-2.5" />
      {meta.label}
    </span>
  );
}

const HEALTH_META: Record<string, { label: string; className: string }> = {
  healthy: { label: "Healthy", className: "bg-data-low-bg text-data-low" },
  attention: { label: "Attention", className: "bg-data-medium-bg text-data-medium" },
  stale: { label: "Stale", className: "bg-data-high-bg text-data-high" },
};

export function HealthChip({
  health,
  className,
}: {
  health?: string | null;
  className?: string;
}) {
  const meta = HEALTH_META[(health ?? "healthy").toLowerCase()] ?? HEALTH_META.healthy;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-caption font-medium",
        meta.className,
        className,
      )}
    >
      {meta.label}
    </span>
  );
}
