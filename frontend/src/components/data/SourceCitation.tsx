import { BookMarked } from "lucide-react";

import { Tooltip } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * Inline citation for an emission factor or figure. Auditability is the product's
 * core promise, so every factor renders one of these.
 */
export function SourceCitation({
  source,
  className,
}: {
  source: string;
  className?: string;
}) {
  if (!source) {
    return (
      <span className={cn("inline-flex items-center gap-1 text-caption text-muted-foreground", className)}>
        <BookMarked className="h-3 w-3" aria-hidden />
        no source
      </span>
    );
  }
  return (
    <Tooltip content={source}>
      <span
        className={cn(
          "inline-flex max-w-full items-center gap-1 font-mono text-caption text-muted-foreground",
          className,
        )}
      >
        <BookMarked className="h-3 w-3 shrink-0" aria-hidden />
        <span className="truncate">{source}</span>
      </span>
    </Tooltip>
  );
}
