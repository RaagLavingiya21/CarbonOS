"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import * as Dialog from "@radix-ui/react-dialog";
import {
  Bot,
  Factory,
  FileSearch,
  LayoutDashboard,
  type LucideIcon,
  MessageSquare,
  Moon,
  Search,
  Settings,
  Sun,
  UploadCloud,
} from "lucide-react";

import { cn } from "@/lib/utils";

interface CommandItem {
  id: string;
  label: string;
  hint: string;
  icon: LucideIcon;
  keywords?: string;
  run: (ctx: CommandContext) => void;
}

interface CommandContext {
  router: ReturnType<typeof useRouter>;
  toggleTheme: () => void;
  close: () => void;
}

const NAV: Array<Omit<CommandItem, "run"> & { href: string }> = [
  { id: "nav-dashboard", label: "Go to Dashboard", hint: "Overview", icon: LayoutDashboard, href: "/" },
  { id: "nav-chat", label: "Open Chat", hint: "Platform assistant", icon: MessageSquare, href: "/chat" },
  { id: "nav-analyzer", label: "Open Analyzer", hint: "BOM footprint", icon: UploadCloud, href: "/analyzer" },
  { id: "nav-gap", label: "Open Gap Analysis", hint: "Scope 3 readiness", icon: FileSearch, href: "/gap-analysis" },
  { id: "nav-advisor", label: "Open Advisor", hint: "Ask questions", icon: Bot, href: "/advisor" },
  { id: "nav-suppliers", label: "Open Supplier Copilot", hint: "Engagement", icon: Factory, href: "/suppliers" },
  { id: "nav-settings", label: "Open Settings", hint: "Workspace & org", icon: Settings, href: "/settings/org" },
];

const ACTIONS: Array<Omit<CommandItem, "run"> & { message?: string }> = [
  { id: "act-bom", label: "Analyze a bill of materials", hint: "Start workflow", icon: UploadCloud, message: "I want to analyze a bill of materials", keywords: "bom upload product" },
  { id: "act-gap", label: "Check my Scope 3 gaps", hint: "Start workflow", icon: FileSearch, message: "Check my Scope 3 gaps", keywords: "gap readiness" },
  { id: "act-email", label: "Draft a supplier email", hint: "Start workflow", icon: Factory, message: "Draft a supplier email", keywords: "supplier engagement outreach" },
];

export function CommandMenu({
  open,
  onOpenChange,
  toggleTheme,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  toggleTheme: () => void;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const items = useMemo<CommandItem[]>(() => {
    const nav = NAV.map((n) => ({
      ...n,
      run: ({ router, close }: CommandContext) => {
        router.push(n.href);
        close();
      },
    }));
    const actions = ACTIONS.map((a) => ({
      ...a,
      run: ({ router, close }: CommandContext) => {
        router.push(`/chat?message=${encodeURIComponent(a.message ?? a.label)}`);
        close();
      },
    }));
    const theme: CommandItem = {
      id: "act-theme",
      label: "Toggle dark mode",
      hint: "Appearance",
      icon: Moon,
      keywords: "theme light dark appearance",
      run: ({ toggleTheme, close }) => {
        toggleTheme();
        close();
      },
    };
    return [...actions, ...nav, theme];
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) =>
      `${item.label} ${item.hint} ${item.keywords ?? ""}`.toLowerCase().includes(q),
    );
  }, [items, query]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    if (open) {
      setQuery("");
      setActive(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  function close() {
    onOpenChange(false);
  }

  function runItem(item: CommandItem | undefined) {
    if (!item) return;
    item.run({ router, toggleTheme, close });
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => Math.min(index + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      runItem(filtered[active]);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-foreground/20 backdrop-blur-[2px] data-[state=open]:animate-fade-in" />
        <Dialog.Content
          onKeyDown={onKeyDown}
          className="fixed left-1/2 top-[18%] z-50 w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 overflow-hidden rounded-lg border bg-popover text-popover-foreground shadow-overlay data-[state=open]:animate-slide-up"
        >
          <Dialog.Title className="sr-only">Command menu</Dialog.Title>
          <Dialog.Description className="sr-only">
            Search to jump to a module or start a workflow.
          </Dialog.Description>
          <div className="flex items-center gap-2 border-b px-3.5">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              ref={inputRef}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search modules and actions…"
              className="h-11 w-full bg-transparent text-small outline-none placeholder:text-muted-foreground"
            />
            <kbd className="hidden rounded border bg-muted px-1.5 py-0.5 text-caption text-muted-foreground sm:inline">
              esc
            </kbd>
          </div>
          <div className="max-h-80 overflow-y-auto p-1.5">
            {filtered.length === 0 ? (
              <p className="px-3 py-6 text-center text-small text-muted-foreground">
                No matches for “{query}”.
              </p>
            ) : (
              filtered.map((item, index) => {
                const Icon = item.icon;
                const isActive = index === active;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onMouseEnter={() => setActive(index)}
                    onClick={() => runItem(item)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-small transition-colors duration-micro",
                      isActive ? "bg-accent text-accent-foreground" : "text-foreground",
                    )}
                  >
                    {item.id === "act-theme" ? (
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center">
                        <Moon className="h-4 w-4 dark:hidden" />
                        <Sun className="hidden h-4 w-4 dark:block" />
                      </span>
                    ) : (
                      <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                    )}
                    <span className="flex-1 truncate">{item.label}</span>
                    <span className="shrink-0 text-caption text-muted-foreground">{item.hint}</span>
                  </button>
                );
              })
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
