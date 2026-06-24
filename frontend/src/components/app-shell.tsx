"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  Bot,
  Factory,
  FileSearch,
  LayoutDashboard,
  LogOut,
  UploadCloud,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { createSupabaseBrowserClient } from "@/lib/supabase";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/analyzer", label: "Analyzer", icon: UploadCloud },
  { href: "/gap-analysis", label: "Gap Analysis", icon: FileSearch },
  { href: "/advisor", label: "Advisor", icon: Bot },
  { href: "/suppliers", label: "Supplier Copilot", icon: Factory },
];

const publicRoutes = ["/login", "/signup"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [email, setEmail] = useState<string | null>(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const supabase = useMemo(() => createSupabaseBrowserClient(), []);
  const isPublicRoute = publicRoutes.includes(pathname);

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
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <div className="h-2 w-52 overflow-hidden rounded-full bg-secondary">
            <div className="h-full w-1/2 animate-pulse rounded-full bg-primary" />
          </div>
          <p className="mt-4 text-sm text-muted-foreground">Checking your workspace...</p>
        </div>
      </div>
    );
  }

  if (!email) return null;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),_transparent_34rem),linear-gradient(180deg,_#f8fafc_0%,_#eef6f3_100%)]">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-72 border-r bg-white/85 p-6 backdrop-blur lg:block">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <BarChart3 className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold">Carbon Analyzer</p>
            <p className="text-xs text-muted-foreground">Scope 3 intelligence</p>
          </div>
        </Link>

        <nav className="mt-10 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active =
              item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted-foreground transition hover:bg-accent hover:text-accent-foreground",
                  active && "bg-accent text-accent-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="absolute bottom-6 left-6 right-6 rounded-xl border bg-secondary/60 p-4">
          <p className="truncate text-sm font-medium">{email}</p>
          <p className="mt-1 text-xs text-muted-foreground">Authenticated via Supabase</p>
          <Button className="mt-4 w-full" variant="outline" onClick={signOut}>
            <LogOut className="h-4 w-4" />
            Sign out
          </Button>
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-30 border-b bg-white/80 backdrop-blur lg:hidden">
          <div className="flex items-center justify-between px-4 py-3">
            <Link href="/" className="font-semibold">
              Carbon Analyzer
            </Link>
            <Button variant="ghost" size="sm" onClick={signOut}>
              Sign out
            </Button>
          </div>
          <nav className="flex gap-2 overflow-x-auto px-4 pb-3">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="whitespace-nowrap rounded-full border bg-white px-3 py-1.5 text-xs font-medium"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="container py-8 lg:py-10">{children}</main>
      </div>
    </div>
  );
}
