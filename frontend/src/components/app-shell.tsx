"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Bot,
  Factory,
  FileSearch,
  Leaf,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Search,
  Settings,
  UploadCloud,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { CommandMenu } from "@/components/layout/CommandMenu";
import { GlobalChatIcon } from "@/components/layout/GlobalChatIcon";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { WorkspaceBadge } from "@/components/layout/WorkspaceBadge";
import { createSupabaseBrowserClient } from "@/lib/supabase";
import { toggleTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/analyzer", label: "Analyzer", icon: UploadCloud },
  { href: "/gap-analysis", label: "Gap Analysis", icon: FileSearch },
  { href: "/advisor", label: "Advisor", icon: Bot },
  { href: "/suppliers", label: "Supplier Copilot", icon: Factory },
  { href: "/settings/org", label: "Settings", icon: Settings },
];

const publicRoutes = ["/login", "/signup"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [cmdkOpen, setCmdkOpen] = useState(false);
  const supabase = useMemo(() => createSupabaseBrowserClient(), []);
  const isPublicRoute = publicRoutes.includes(pathname);

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
      if (!userEmail && !isPublicRoute) router.replace("/login");
      if (userEmail && isPublicRoute) router.replace("/");
    });

    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      const userEmail = session?.user.email ?? null;
      setEmail(userEmail);
      if (!userEmail && !isPublicRoute) router.replace("/login");
    });

    return () => {
      mounted = false;
      listener.subscription.unsubscribe();
    };
  }, [isPublicRoute, router, supabase]);

  async function signOut() {
    await supabase.auth.signOut();
    router.replace("/login");
  }

  if (isPublicRoute) {
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

  if (!email) return null;

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r bg-card px-4 py-5 lg:block">
        <Link href="/" className="flex items-center gap-2.5 px-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Leaf className="h-5 w-5" />
          </div>
          <div className="leading-tight">
            <p className="font-display text-body font-medium">Carbon Analyzer</p>
            <p className="text-caption text-muted-foreground">Scope 3 intelligence</p>
          </div>
        </Link>

        <nav className="mt-8 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "relative flex items-center gap-3 rounded-md px-3 py-2 text-small font-medium text-muted-foreground transition-colors duration-micro ease-out hover:bg-secondary hover:text-foreground",
                  active &&
                    "bg-secondary text-foreground before:absolute before:left-0 before:top-1/2 before:h-4 before:w-0.5 before:-translate-y-1/2 before:rounded-full before:bg-primary",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-5 left-4 right-4 rounded-md border bg-background p-3">
          <p className="truncate text-small font-medium">{email}</p>
          <p className="mt-0.5 text-caption text-muted-foreground">Signed in</p>
          <Button className="mt-3 w-full" variant="outline" size="sm" onClick={signOut}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 border-b bg-background/90 backdrop-blur-sm">
          <div className="hidden items-center justify-between gap-2 px-6 py-2.5 lg:flex">
            <button
              type="button"
              onClick={() => setCmdkOpen(true)}
              className="flex h-8 w-64 items-center gap-2 rounded-md border bg-card px-3 text-small text-muted-foreground transition-colors duration-micro hover:border-border hover:text-foreground"
            >
              <Search className="h-4 w-4" />
              <span className="flex-1 text-left">Search or jump to…</span>
              <kbd className="rounded border bg-muted px-1.5 py-0.5 text-caption">⌘K</kbd>
            </button>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <WorkspaceBadge />
            </div>
          </div>
          <div className="flex items-center justify-between px-4 py-2.5 lg:hidden">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Leaf className="h-4 w-4" />
              </div>
              <span className="font-display font-medium">Carbon Analyzer</span>
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
                      : "bg-card text-muted-foreground",
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </header>
        <main className="container py-8 lg:py-10">{children}</main>
      </div>
      {pathname !== "/chat" ? <GlobalChatIcon /> : null}
      <CommandMenu open={cmdkOpen} onOpenChange={setCmdkOpen} toggleTheme={toggleTheme} />
    </div>
  );
}
