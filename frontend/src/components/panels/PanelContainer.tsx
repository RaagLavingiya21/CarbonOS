"use client";

import { X } from "lucide-react";

import { BOMPanel } from "@/components/panels/BOMPanel";
import { GapAnalyzerPanel } from "@/components/panels/GapAnalyzerPanel";
import { SupplierCopilotPanel } from "@/components/panels/SupplierCopilotPanel";
import {
  MODULE_LABELS,
  usePanels,
} from "@/components/panels/PanelContext";
import { PanelTabs } from "@/components/panels/PanelTabs";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function PanelContainer() {
  const { activePanel, closePanel, updatePanelState } = usePanels();

  if (!activePanel) return null;

  const label =
    MODULE_LABELS[activePanel.module_type] ?? activePanel.module_type;

  return (
    <div className="flex h-full min-h-[460px] flex-col bg-card">
      <PanelTabs />
      <div className="flex flex-1 flex-col overflow-y-auto p-4">
        {activePanel.module_type === "bom_analyzer" ? (
          <BOMPanel
            panel={activePanel}
            onClose={() => closePanel(activePanel.panel_id)}
            onStateChange={(partial) =>
              updatePanelState(activePanel.panel_id, partial)
            }
          />
        ) : activePanel.module_type === "gap_analyzer" ? (
          <GapAnalyzerPanel
            panel={activePanel}
            onClose={() => closePanel(activePanel.panel_id)}
            onStateChange={(partial) =>
              updatePanelState(activePanel.panel_id, partial)
            }
          />
        ) : activePanel.module_type === "supplier_copilot" ? (
          <SupplierCopilotPanel
            panel={activePanel}
            onClose={() => closePanel(activePanel.panel_id)}
            onStateChange={(partial) =>
              updatePanelState(activePanel.panel_id, partial)
            }
          />
        ) : (
          <Card>
            <CardHeader className="flex flex-row items-start justify-between space-y-0">
              <div>
                <CardTitle>{label}</CardTitle>
                <CardDescription>
                  Module panel placeholder — content will be added in a later
                  step.
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="shrink-0"
                aria-label={`Close ${label}`}
                onClick={() => closePanel(activePanel.panel_id)}
              >
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Panel ID:{" "}
                <code className="rounded bg-secondary px-1.5 py-0.5 text-xs">
                  {activePanel.panel_id.slice(0, 8)}…
                </code>
              </p>
              {Object.keys(activePanel.panel_state).length > 0 ? (
                <pre className="mt-4 max-h-48 overflow-auto rounded-lg bg-secondary/50 p-3 text-xs">
                  {JSON.stringify(activePanel.panel_state, null, 2)}
                </pre>
              ) : null}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
