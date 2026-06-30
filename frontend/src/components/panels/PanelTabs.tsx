"use client";

import { X } from "lucide-react";

import {
  MODULE_LABELS,
  usePanels,
} from "@/components/panels/PanelContext";
import { cn } from "@/lib/utils";

export function PanelTabs() {
  const { openPanels, activePanelId, switchPanel, closePanel } = usePanels();

  if (openPanels.length === 0) return null;

  return (
    <div className="flex items-end gap-0.5 overflow-x-auto border-b bg-secondary/30 px-2 pt-2">
      {openPanels.map((panel) => {
        const isActive = panel.panel_id === activePanelId;
        const label = MODULE_LABELS[panel.module_type] ?? panel.module_type;

        return (
          <div
            key={panel.panel_id}
            className={cn(
              "group flex max-w-[200px] shrink-0 items-center gap-1 rounded-t-lg border border-b-0 px-3 py-2 text-sm transition-colors",
              isActive
                ? "border-border bg-card font-medium text-foreground shadow-xs"
                : "border-transparent bg-secondary/60 text-muted-foreground hover:bg-secondary",
            )}
          >
            <button
              type="button"
              className="min-w-0 flex-1 truncate text-left"
              onClick={() => switchPanel(panel.panel_id)}
            >
              {label}
            </button>
            <button
              type="button"
              className={cn(
                "rounded p-0.5 opacity-60 transition-opacity hover:bg-muted hover:opacity-100",
                isActive && "opacity-80",
              )}
              aria-label={`Close ${label}`}
              onClick={(event) => {
                event.stopPropagation();
                closePanel(panel.panel_id);
              }}
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
