import * as React from "react";

import { cn } from "@/lib/utils";

/**
 * Lightweight CSS-only tooltip — no external dependency.
 * Shows on hover and keyboard focus; content is also exposed via title for AT.
 */
export function Tooltip({
  content,
  children,
  side = "top",
  className,
}: {
  content: React.ReactNode;
  children: React.ReactNode;
  side?: "top" | "bottom";
  className?: string;
}) {
  return (
    <span className={cn("group/tt relative inline-flex", className)} tabIndex={0}>
      {children}
      <span
        role="tooltip"
        className={cn(
          "pointer-events-none absolute left-1/2 z-50 w-max max-w-xs -translate-x-1/2 scale-95 rounded-md border bg-popover px-2.5 py-1.5 text-caption text-popover-foreground opacity-0 shadow-overlay transition duration-micro ease-out group-hover/tt:scale-100 group-hover/tt:opacity-100 group-focus/tt:scale-100 group-focus/tt:opacity-100",
          side === "top" ? "bottom-full mb-1.5" : "top-full mt-1.5",
        )}
      >
        {content}
      </span>
    </span>
  );
}
