"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type { ModuleType } from "@/lib/chat-api";

export const MODULE_LABELS: Record<ModuleType, string> = {
  bom_analyzer: "BOM Analyzer",
  gap_analyzer: "Gap Analyzer",
  supplier_copilot: "Supplier Copilot",
  advisor: "Advisor",
};

export interface Panel {
  panel_id: string;
  module_type: ModuleType;
  panel_state: Record<string, unknown>;
}

interface PanelContextValue {
  openPanels: Panel[];
  activePanelId: string | null;
  activePanel: Panel | null;
  openPanel: (
    moduleType: ModuleType,
    state?: Record<string, unknown>,
  ) => void;
  closePanel: (panelId: string) => void;
  switchPanel: (panelId: string) => void;
}

const PanelContext = createContext<PanelContextValue | null>(null);

export function PanelProvider({ children }: { children: ReactNode }) {
  const [openPanels, setOpenPanels] = useState<Panel[]>([]);
  const [activePanelId, setActivePanelId] = useState<string | null>(null);

  const openPanel = useCallback(
    (moduleType: ModuleType, state: Record<string, unknown> = {}) => {
      setOpenPanels((current) => {
        const existing = current.find((p) => p.module_type === moduleType);
        if (existing) {
          setActivePanelId(existing.panel_id);
          if (Object.keys(state).length > 0) {
            return current.map((p) =>
              p.panel_id === existing.panel_id
                ? { ...p, panel_state: { ...p.panel_state, ...state } }
                : p,
            );
          }
          return current;
        }

        const newPanel: Panel = {
          panel_id: crypto.randomUUID(),
          module_type: moduleType,
          panel_state: state,
        };
        setActivePanelId(newPanel.panel_id);
        return [...current, newPanel];
      });
    },
    [],
  );

  const closePanel = useCallback((panelId: string) => {
    setOpenPanels((current) => {
      const remaining = current.filter((p) => p.panel_id !== panelId);
      setActivePanelId((activeId) => {
        if (activeId !== panelId) return activeId;
        return remaining.length > 0
          ? remaining[remaining.length - 1].panel_id
          : null;
      });
      return remaining;
    });
  }, []);

  const switchPanel = useCallback((panelId: string) => {
    setActivePanelId(panelId);
  }, []);

  const activePanel = useMemo(
    () => openPanels.find((p) => p.panel_id === activePanelId) ?? null,
    [openPanels, activePanelId],
  );

  const value = useMemo(
    () => ({
      openPanels,
      activePanelId,
      activePanel,
      openPanel,
      closePanel,
      switchPanel,
    }),
    [openPanels, activePanelId, activePanel, openPanel, closePanel, switchPanel],
  );

  return (
    <PanelContext.Provider value={value}>{children}</PanelContext.Provider>
  );
}

export function usePanels() {
  const context = useContext(PanelContext);
  if (!context) {
    throw new Error("usePanels must be used within a PanelProvider");
  }
  return context;
}
