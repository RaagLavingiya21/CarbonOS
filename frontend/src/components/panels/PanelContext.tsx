"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  chatApi,
  type IntakeSubmitPayload,
  type ModuleType,
} from "@/lib/chat-api";

export const MODULE_LABELS: Record<ModuleType, string> = {
  bom_analyzer: "BOM Analyzer",
  gap_analyzer: "Gap Analyzer",
  supplier_copilot: "Supplier Copilot",
  advisor: "Advisor",
};

const PATCH_DEBOUNCE_MS = 500;

export interface Panel {
  panel_id: string;
  backend_panel_id?: string;
  thread_id?: string | null;
  module_type: ModuleType;
  panel_state: Record<string, unknown>;
  intake?: IntakeSubmitPayload;
}

interface PanelContextValue {
  openPanels: Panel[];
  activePanelId: string | null;
  activePanel: Panel | null;
  panelsLoading: boolean;
  openPanel: (
    moduleType: ModuleType,
    state?: Record<string, unknown>,
    intake?: IntakeSubmitPayload,
    threadId?: string | null,
  ) => void;
  closePanel: (panelId: string) => void;
  switchPanel: (panelId: string) => void;
  updatePanelState: (
    panelId: string,
    partial: Record<string, unknown>,
  ) => void;
}

const PanelContext = createContext<PanelContextValue | null>(null);

function isModuleType(value: string): value is ModuleType {
  return (
    value === "bom_analyzer" ||
    value === "gap_analyzer" ||
    value === "supplier_copilot" ||
    value === "advisor"
  );
}

export function PanelProvider({ children }: { children: ReactNode }) {
  const [openPanels, setOpenPanels] = useState<Panel[]>([]);
  const [activePanelId, setActivePanelId] = useState<string | null>(null);
  const [panelsLoading, setPanelsLoading] = useState(true);

  const openPanelsRef = useRef<Panel[]>([]);
  const debounceTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );
  const pendingPanelStateRef = useRef<Map<string, Record<string, unknown>>>(
    new Map(),
  );
  const createPromisesRef = useRef<Map<string, Promise<string | null>>>(
    new Map(),
  );

  useEffect(() => {
    openPanelsRef.current = openPanels;
  }, [openPanels]);

  const flushPendingPatch = useCallback(async (clientPanelId: string) => {
    const panel = openPanelsRef.current.find((p) => p.panel_id === clientPanelId);
    if (!panel?.backend_panel_id) return;

    const pending = pendingPanelStateRef.current.get(clientPanelId);
    if (!pending) return;

    pendingPanelStateRef.current.delete(clientPanelId);
    try {
      await chatApi.updatePanel(panel.backend_panel_id, {
        panel_state: { ...panel.panel_state, ...pending },
      });
    } catch (err) {
      console.error("Failed to persist panel state:", err);
    }
  }, []);

  const schedulePatch = useCallback(
    (clientPanelId: string, mergedState: Record<string, unknown>) => {
      pendingPanelStateRef.current.set(clientPanelId, mergedState);

      const existingTimer = debounceTimersRef.current.get(clientPanelId);
      if (existingTimer) clearTimeout(existingTimer);

      debounceTimersRef.current.set(
        clientPanelId,
        setTimeout(() => {
          debounceTimersRef.current.delete(clientPanelId);
          void flushPendingPatch(clientPanelId);
        }, PATCH_DEBOUNCE_MS),
      );
    },
    [flushPendingPatch],
  );

  const persistCreate = useCallback(
    (
      clientPanelId: string,
      moduleType: ModuleType,
      panelState: Record<string, unknown>,
      threadId?: string | null,
      tabOrder = 0,
    ) => {
      const promise = chatApi
        .createPanel({
          module_type: moduleType,
          thread_id: threadId ?? null,
          panel_state: panelState,
          tab_order: tabOrder,
          is_active: true,
        })
        .then((created) => {
          setOpenPanels((current) =>
            current.map((p) =>
              p.panel_id === clientPanelId
                ? { ...p, backend_panel_id: created.panel_id }
                : p,
            ),
          );

          const pending = pendingPanelStateRef.current.get(clientPanelId);
          if (pending) {
            void chatApi
              .updatePanel(created.panel_id, { panel_state: pending })
              .catch((err) =>
                console.error("Failed to flush pending panel state:", err),
              );
          }

          return created.panel_id;
        })
        .catch((err) => {
          console.error("Failed to create panel:", err);
          return null;
        })
        .finally(() => {
          createPromisesRef.current.delete(clientPanelId);
        });

      createPromisesRef.current.set(clientPanelId, promise);
      return promise;
    },
    [],
  );

  useEffect(() => {
    let cancelled = false;

    async function loadPanels() {
      setPanelsLoading(true);
      try {
        const rows = await chatApi.listPanels();
        if (cancelled) return;

        const restored: Panel[] = rows
          .filter((row) => isModuleType(row.module_type))
          .map((row) => ({
            panel_id: crypto.randomUUID(),
            backend_panel_id: row.panel_id,
            thread_id: row.thread_id,
            module_type: row.module_type,
            panel_state: row.panel_state ?? {},
            intake: undefined,
          }));

        setOpenPanels(restored);

        const activeBackend = rows.find((row) => row.is_active);
        if (activeBackend) {
          const match = restored.find(
            (p) => p.backend_panel_id === activeBackend.panel_id,
          );
          setActivePanelId(match?.panel_id ?? restored.at(-1)?.panel_id ?? null);
        } else {
          setActivePanelId(restored.at(-1)?.panel_id ?? null);
        }
      } catch (err) {
        console.error("Failed to load panels:", err);
      } finally {
        if (!cancelled) setPanelsLoading(false);
      }
    }

    void loadPanels();
    return () => {
      cancelled = true;
    };
  }, []);

  const openPanel = useCallback(
    (
      moduleType: ModuleType,
      state: Record<string, unknown> = {},
      intake?: IntakeSubmitPayload,
      threadId?: string | null,
    ) => {
      setOpenPanels((current) => {
        const existing = current.find((p) => p.module_type === moduleType);
        if (existing) {
          const mergedState = { ...existing.panel_state, ...state };
          setActivePanelId(existing.panel_id);
          schedulePatch(existing.panel_id, mergedState);
          if (existing.backend_panel_id) {
            void chatApi
              .updatePanel(existing.backend_panel_id, {
                panel_state: mergedState,
                is_active: true,
              })
              .catch((err) =>
                console.error("Failed to update existing panel:", err),
              );
          }
          return current.map((p) =>
            p.panel_id === existing.panel_id
              ? {
                  ...p,
                  panel_state: mergedState,
                  intake: intake ?? p.intake,
                  thread_id: threadId ?? p.thread_id,
                }
              : p,
          );
        }

        const clientPanelId = crypto.randomUUID();
        const newPanel: Panel = {
          panel_id: clientPanelId,
          module_type: moduleType,
          panel_state: state,
          intake,
          thread_id: threadId ?? null,
        };
        setActivePanelId(clientPanelId);
        void persistCreate(
          clientPanelId,
          moduleType,
          state,
          threadId,
          current.length,
        );
        return [...current, newPanel];
      });
    },
    [persistCreate, schedulePatch],
  );

  const closePanel = useCallback((panelId: string) => {
    const panel = openPanelsRef.current.find((p) => p.panel_id === panelId);
    if (!panel) return;

    const timer = debounceTimersRef.current.get(panelId);
    if (timer) {
      clearTimeout(timer);
      debounceTimersRef.current.delete(panelId);
    }
    pendingPanelStateRef.current.delete(panelId);

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

    void (async () => {
      let backendId = panel.backend_panel_id;
      if (!backendId) {
        const createPromise = createPromisesRef.current.get(panelId);
        if (createPromise) {
          backendId = (await createPromise) ?? undefined;
        }
      }
      if (backendId) {
        try {
          await chatApi.deletePanel(backendId);
        } catch (err) {
          console.error("Failed to delete panel:", err);
        }
      }
    })();
  }, []);

  const switchPanel = useCallback((panelId: string) => {
    setActivePanelId(panelId);

    const panel = openPanelsRef.current.find((p) => p.panel_id === panelId);
    if (!panel?.backend_panel_id) return;

    void chatApi
      .updatePanel(panel.backend_panel_id, { is_active: true })
      .catch((err) => console.error("Failed to mark panel active:", err));

    for (const other of openPanelsRef.current) {
      if (
        other.panel_id !== panelId &&
        other.backend_panel_id &&
        other.backend_panel_id !== panel.backend_panel_id
      ) {
        void chatApi
          .updatePanel(other.backend_panel_id, { is_active: false })
          .catch((err) => console.error("Failed to mark panel inactive:", err));
      }
    }
  }, []);

  const updatePanelState = useCallback(
    (panelId: string, partial: Record<string, unknown>) => {
      setOpenPanels((current) => {
        const updated = current.map((p) =>
          p.panel_id === panelId
            ? { ...p, panel_state: { ...p.panel_state, ...partial } }
            : p,
        );
        const panel = updated.find((p) => p.panel_id === panelId);
        if (panel) {
          schedulePatch(panelId, panel.panel_state);
        }
        return updated;
      });
    },
    [schedulePatch],
  );

  const activePanel = useMemo(
    () => openPanels.find((p) => p.panel_id === activePanelId) ?? null,
    [openPanels, activePanelId],
  );

  const value = useMemo(
    () => ({
      openPanels,
      activePanelId,
      activePanel,
      panelsLoading,
      openPanel,
      closePanel,
      switchPanel,
      updatePanelState,
    }),
    [
      openPanels,
      activePanelId,
      activePanel,
      panelsLoading,
      openPanel,
      closePanel,
      switchPanel,
      updatePanelState,
    ],
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
