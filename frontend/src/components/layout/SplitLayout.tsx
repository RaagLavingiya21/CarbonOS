"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { usePanels } from "@/components/panels/PanelContext";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "chat-split-width";
const DEFAULT_CHAT_WIDTH = 0.4;
const MIN_CHAT_WIDTH = 0.25;
const MAX_CHAT_WIDTH = 0.75;

interface SplitLayoutProps {
  chat: ReactNode;
  panel: ReactNode;
}

function readStoredWidth(): number {
  if (typeof window === "undefined") return DEFAULT_CHAT_WIDTH;
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return DEFAULT_CHAT_WIDTH;
  const parsed = Number.parseFloat(stored);
  if (Number.isNaN(parsed)) return DEFAULT_CHAT_WIDTH;
  return Math.min(MAX_CHAT_WIDTH, Math.max(MIN_CHAT_WIDTH, parsed));
}

export function SplitLayout({ chat, panel }: SplitLayoutProps) {
  const { openPanels } = usePanels();
  const hasPanels = openPanels.length > 0;

  const containerRef = useRef<HTMLDivElement>(null);
  const [chatWidthFraction, setChatWidthFraction] = useState(DEFAULT_CHAT_WIDTH);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    setChatWidthFraction(readStoredWidth());
  }, []);

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragging(true);
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [],
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging || !containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const fraction = (event.clientX - rect.left) / rect.width;
      const clamped = Math.min(
        MAX_CHAT_WIDTH,
        Math.max(MIN_CHAT_WIDTH, fraction),
      );
      setChatWidthFraction(clamped);
    },
    [isDragging],
  );

  const handlePointerUp = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!isDragging) return;
      setIsDragging(false);
      event.currentTarget.releasePointerCapture(event.pointerId);
      localStorage.setItem(STORAGE_KEY, String(chatWidthFraction));
    },
    [isDragging, chatWidthFraction],
  );

  return (
    <div
      ref={containerRef}
      className={cn(
        "flex min-h-0 flex-1 w-full",
        isDragging && "select-none",
      )}
    >
      <div
        className="flex min-w-0 flex-col overflow-hidden transition-[width] duration-300 ease-in-out"
        style={{ width: hasPanels ? `${chatWidthFraction * 100}%` : "100%" }}
      >
        {chat}
      </div>

      {hasPanels ? (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize chat and panel"
            className={cn(
              "group relative z-10 w-1 shrink-0 cursor-col-resize bg-border transition-colors hover:bg-primary/40",
              isDragging && "bg-primary/50",
            )}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
          >
            <div className="absolute inset-y-0 -left-1 -right-1" />
          </div>

          <div
            className="flex min-w-0 flex-col overflow-hidden transition-[width] duration-300 ease-in-out"
            style={{ width: `${(1 - chatWidthFraction) * 100}%` }}
          >
            {panel}
          </div>
        </>
      ) : null}
    </div>
  );
}
