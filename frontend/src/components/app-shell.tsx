"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  Bot,
  BarChart3,
  Boxes,
  Factory,
  FileSearch,
  Flame,
  Inbox,
  Layers,
  Leaf,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Plus,
  Search,
  Settings,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { CommandMenu } from "@/components/layout/CommandMenu";
import { LandingPage } from "@/components/marketing/LandingPage";
import { GlobalChatIcon } from "@/components/layout/GlobalChatIcon";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { WorkspaceBadge } from "@/components/layout/WorkspaceBadge";
import { PortfolioNav } from "@/components/portfolio/PortfolioNav";
import { createSupabaseBrowserClient } from "@/lib/supabase";
import { toggleTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

// Scope 2 ("Grid") module nav entry — gated so it can ship dark in prod until
// design-partner pilots. Enable with NEXT_PUBLIC_SCOPE2_ENABLED=true.
const SCOPE2_ENABLED = process.env.NEXT_PUBLIC_SCOPE2_ENABLED === "true";
// Scope 3 module nav entry — ships dark until GA. Enable with NEXT_PUBLIC_SCOPE3_ENABLED=true.
const SCOPE3_ENABLED = process.env.NEXT_PUBLIC_SCOPE3_ENABLED === "true";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, shortcut: "G D" },
  { href: "/chat", label: "Chat", icon: MessageSquare, shortcut: "G C" },
  { href: "/products", label: "Portfolio", icon: Boxes, shortcut: "G P" },
  { href: "/requests", label: "Requests", icon: Inbox, shortcut: "G R" },
  { href: "/rollup", label: "Corporate footprint", icon: BarChart3, shortcut: "G F" },
  // Scope 1 ships dark: nav hidden unless the feature flag is explicitly on.
  ...(process.env.NEXT_PUBLIC_SCOPE1_ENABLED === "true"
    ? [{ href: "/scope-1", label: "Scope 1", icon: Flame, shortcut: "G 1" }]
    : []),
  { href: "/gap-analysis", label: "Gap Analysis", icon: FileSearch, shortcut: "G G" },
  { href: "/advisor", label: "Advisor", icon: Bot, shortcut: "G V" },
  { href: "/suppliers", label: "Supplier Copilot", icon: Factory, shortcut: "G S" },
  ...(SCOPE2_ENABLED
    ? [{ href: "/scope-2", label: "Scope 2", icon: Zap, shortcut: "G 2" }]
    : []),
  ...(SCOPE3_ENABLED
    ? [{ href: "/scope-3", label: "Scope 3", icon: Layers, shortcut: "G 3" }]
    : []),
  { href: "/settings/org", label: "Settings", icon: Settings, shortcut: "" },
];

const publicRoutes = ["/login", "/signup"];
// Routes rendered bare (no app chrome) and reachable by anyone, logged in or out.
const bareRoutes = ["/demo"];
const bareRoutePrefixes = ["/shared", "/request"];

function initialsFromEmail(email: string): string {
  const local = email.split("@")[0] ?? email;
  const parts = local.split(/[.\-_]+/).filter(Boolean);
  const letters = (parts.length > 1 ? parts[0][0] + parts[1][0] : local.slice(0, 2)) ?? "";
  return letters.toUpperCase();
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const supabase = useMemo(() => createSupabaseBrowserClient(), []);
  const isPublicRoute = publicRoutes.includes(pathname);
  const isBareRoute =
    bareRoutes.includes(pathname) ||
    bareRoutePrefixes.some((prefix) => pathname.startsWith(prefix));
  // Logged-out visitors see the marketing landing page at "/"; logged-in
  // visitors see the dashboard there.
  const isLandingRoute = pathname === "/";
  // Chat is a full-height app, not a scrolling document — it gets the
  // whole space below the header instead of the standard container.
  const isChatRoute = pathname === "/chat";

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCmdkOpen((open) => !open);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    let mounted = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      const userEmail = data.session?.user.email ?? null;
      setEmail(userEmail);
      setCheckingAuth(false);
      if (!userEmail && !isPublicRoute && !isLandingRoute && !isBareRoute)
        router.replace("/login");
      if (userEmail && isPublicRoute) router.replace("/");
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      const userEmail = session?.user.email ?? null;
      setEmail(userEmail);
      if (!userEmail && !isPublicRoute && !isLandingRoute && !isBareRoute)
        router.replace("/login");
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, [isPublicRoute, isLandingRoute, isBareRoute, router, supabase]);

  async function signOut() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (isPublicRoute || isBareRoute) {
    return <>{children}</>;
  }

  if (checkingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="rounded-lg border bg-card p-6 shadow-xs">
          <div className="h-1.5 w-52 overflow-hidden rounded-full bg-secondary">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-primary" />
          </div>
          <p className="mt-4 text-small text-muted-foreground">Checking your workspace…</p>
        </div>
      </div>
    );
  }

  // Logged-out visitor on "/" → marketing landing page (no app chrome).
  if (!email && isLandingRoute) {
    return <LandingPage />;
  }

  if (!email) return null;

  const currentNav = navItems.find((item) =>
    item.href === "/" ? pathname === "/" : pathname.startsWith(item.href),
  );
  const breadcrumb =
    currentNav?.label ?? (pathname.startsWith("/analyzer") ? "Portfolio" : "");

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar (desktop) */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[232px] flex-col border-r border-border bg-surface-2 lg:flex">
        <div className="flex h-14 items-center gap-2.5 px-3">
          <Link href="/" className="flex min-w-0 items-center gap-2.5">
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground">
              <Leaf className="h-4 w-4" />
            </span>
            <span className="flex min-w-0 flex-col leading-tight">
              <span className="truncate text-small font-semibold text-foreground">
                Carbon Analyzer
              </span>
              <span className="truncate text-caption text-muted-foreground">
                Scope 3 workspace
              </span>
            </span>
          </Link>
        </div>

        <div className="px-3 pb-2">
          <button
            type="button"
            onClick={() => setCmdkOpen(true)}
            className="flex w-full items-center gap-2 rounded-md border border-border bg-surface px-2.5 py-1.5 text-left text-small text-muted-foreground shadow-xs transition-colors hover:bg-muted hover:text-foreground"
          >
            <Search className="h-3.5 w-3.5" />
            <span className="flex-1">Search or jump to</span>
            <span className="kbd">⌘K</span>
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pt-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            if (item.href === "/products") {
              return <PortfolioNav key={item.href} pathname={pathname} />;
            }
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "group/nav relative flex items-center gap-2.5 rounded-md px-3 py-1.5 text-small font-medium text-muted-foreground transition-colors duration-micro ease-out hover:bg-secondary hover:text-foreground",
                  active &&
                    "bg-secondary text-foreground before:absolute before:left-0 before:top-1/2 before:h-4 before:w-0.5 before:-translate-y-1/2 before:rounded-full before:bg-primary",
                )}
              >
                <Icon className="h-4 w-4 shrink-0 opacity-80" />
                <span className="flex-1 truncate">{item.label}</span>
                {item.shortcut ? (
                  <span className="font-mono text-[10px] text-muted-foreground opacity-0 transition-opacity group-hover/nav:opacity-100">
                    {item.shortcut}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-border p-2">
          <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
            <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-primary/10 text-[10px] font-semibold text-primary">
              {initialsFromEmail(email)}
            </span>
            <span className="min-w-0 flex-1 leading-tight">
              <span className="block truncate text-caption font-medium text-foreground">
                {email}
              </span>
              <span className="block text-[10.5px] text-muted-foreground">Signed in</span>
            </span>
            <button
              type="button"
              onClick={signOut}
              title="Sign out"
              aria-label="Sign out"
              className="grid h-6 w-6 shrink-0 place-items-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </aside>

      <div
        className={cn(
          "lg:pl-[232px]",
          isChatRoute && "flex h-screen flex-col overflow-hidden",
        )}
      >
        <header className="sticky top-0 z-30 shrink-0 border-b border-border bg-background/85 backdrop-blur">
          {/* Desktop top bar */}
          <div className="hidden h-12 items-center gap-3 px-5 lg:flex">
            <nav className="flex items-center gap-1.5 text-small text-muted-foreground">
              {breadcrumb ? (
                <span className="font-medium text-foreground">{breadcrumb}</span>
              ) : null}
            </nav>
            <div className="ml-auto flex items-center gap-1.5">
              <Link
                href="/analyzer"
                className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1 text-small font-medium text-foreground shadow-xs transition-colors hover:bg-muted"
              >
                <Plus className="h-3.5 w-3.5" />
                New footprint
                <span className="kbd ml-1">N</span>
              </Link>
              <WorkspaceBadge />
              <ThemeToggle />
              <button
                type="button"
                title="Notifications"
                aria-label="Notifications"
                className="grid h-7 w-7 place-items-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <Bell className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Mobile top bar */}
          <div className="flex items-center justify-between px-4 py-2.5 lg:hidden">
            <Link href="/" className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
                <Leaf className="h-4 w-4" />
              </span>
              <span className="font-display font-semibold">Carbon Analyzer</span>
            </Link>
            <div className="flex items-center gap-1.5">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Search or jump to"
                onClick={() => setCmdkOpen(true)}
              >
                <Search className="h-4 w-4" />
              </Button>
              <ThemeToggle />
              <WorkspaceBadge />
              <Button variant="ghost" size="sm" onClick={signOut}>
                Sign out
              </Button>
            </div>
          </div>
          <nav className="flex gap-1.5 overflow-x-auto px-4 pb-2.5 lg:hidden">
            {navItems.map((item) => {
              const active =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "whitespace-nowrap rounded-full border px-3 py-1.5 text-caption font-medium transition-colors duration-micro",
                    active
                      ? "border-primary/30 bg-accent text-accent-foreground"
                      : "bg-surface text-muted-foreground",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main
          className={
            isChatRoute
              ? "min-h-0 flex-1 overflow-hidden"
              : "mx-auto max-w-[1440px] px-6 py-6 lg:px-8"
          }
        >
          {children}
        </main>
      </div>
      {pathname !== "/chat" ? <GlobalChatIcon /> : null}
      <CommandMenu open={cmdkOpen} onOpenChange={setCmdkOpen} toggleTheme={toggleTheme} />
    </div>
  );
}
