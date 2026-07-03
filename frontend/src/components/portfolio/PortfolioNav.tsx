"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Boxes, ChevronDown, ChevronRight } from "lucide-react";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

/**
 * Sidebar "Portfolio" item with a collapsible status sub-tree. Child counts are
 * the real `counts_by_status` from the portfolio summary, fetched lazily the
 * first time the group is expanded (so unrelated pages don't pay for it).
 */
const STATUS_CHILDREN: { key: string; label: string; dot: string }[] = [
  { key: "draft", label: "Draft", dot: "bg-muted-foreground/50" },
  { key: "calculated", label: "Calculated", dot: "bg-data-info" },
  { key: "under_review", label: "Under review", dot: "bg-data-medium" },
  { key: "approved", label: "Approved", dot: "bg-data-low" },
  { key: "published", label: "Published", dot: "bg-primary" },
  { key: "flagged", label: "Flagged", dot: "bg-data-high" },
];

export function PortfolioNav({ pathname }: { pathname: string }) {
  const active = pathname.startsWith("/products");
  const [open, setOpen] = useState(active);
  const [counts, setCounts] = useState<Record<string, number> | null>(null);
  const [total, setTotal] = useState<number | null>(null);
  const [fetched, setFetched] = useState(false);

  useEffect(() => {
    if (!open || fetched) return;
    setFetched(true);
    api
      .getPortfolioSummary()
      .then((summary) => {
        setCounts(summary.counts_by_status ?? {});
        setTotal(summary.product_count);
      })
      .catch(() => {
        // Sub-tree counts are best-effort; the links still work without them.
      });
  }, [open, fetched]);

  const visibleChildren = STATUS_CHILDREN.filter(
    (child) => !counts || (counts[child.key] ?? 0) > 0,
  );

  return (
    <div>
      <div className="group relative flex items-center">
        <Link
          href="/products"
          className={cn(
            "relative flex flex-1 items-center gap-3 rounded-md px-3 py-2 text-small font-medium text-muted-foreground transition-colors duration-micro ease-out hover:bg-secondary hover:text-foreground",
            active &&
              "bg-secondary text-foreground before:absolute before:left-0 before:top-1/2 before:h-4 before:w-0.5 before:-translate-y-1/2 before:rounded-full before:bg-primary",
          )}
        >
          <Boxes className="h-4 w-4" />
          <span className="flex-1">Portfolio</span>
        </Link>
        <button
          type="button"
          aria-label={open ? "Collapse portfolio" : "Expand portfolio"}
          onClick={() => setOpen((v) => !v)}
          className="grid h-6 w-6 place-items-center rounded text-muted-foreground hover:bg-secondary hover:text-foreground"
        >
          {open ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {open ? (
        <div className="mb-1 mt-0.5 space-y-0.5 pl-7">
          <Link
            href="/products"
            className="flex items-center gap-2 rounded-md px-3 py-1 text-caption text-muted-foreground hover:bg-secondary hover:text-foreground"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            <span className="flex-1">All products</span>
            {total !== null ? <span className="num">{total}</span> : null}
          </Link>
          {visibleChildren.map((child) => (
            <Link
              key={child.key}
              href={`/products?status=${child.key}`}
              className="flex items-center gap-2 rounded-md px-3 py-1 text-caption text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", child.dot)} />
              <span className="flex-1">{child.label}</span>
              {counts ? <span className="num">{counts[child.key] ?? 0}</span> : null}
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
