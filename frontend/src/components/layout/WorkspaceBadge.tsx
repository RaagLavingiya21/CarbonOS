"use client";

import { useCallback, useEffect, useState } from "react";
import { Building2, ChevronDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Organization,
  getMyOrg,
  setActiveOrg,
  workspaceLabel,
} from "@/lib/org-api";

export function WorkspaceBadge() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [activeOrg, setActiveOrgState] = useState<Organization | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState(false);

  const load = useCallback(async () => {
    try {
      const detail = await getMyOrg();
      setOrgs(detail.orgs);
      setActiveOrgState(detail.active_org);
    } catch {
      setOrgs([]);
      setActiveOrgState(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSwitch(orgId: string) {
    if (orgId === activeOrg?.id) {
      setOpen(false);
      return;
    }
    setSwitching(true);
    try {
      const org = await setActiveOrg(orgId);
      setActiveOrgState(org);
      setOpen(false);
      window.dispatchEvent(new CustomEvent("workspace-changed"));
    } finally {
      setSwitching(false);
    }
  }

  if (loading || !activeOrg) {
    return null;
  }

  const canSwitch = orgs.length > 1;

  return (
    <div className="relative">
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="gap-2"
        disabled={switching}
        onClick={() => canSwitch && setOpen((value) => !value)}
      >
        <Building2 className="h-4 w-4" />
        <span className="max-w-[200px] truncate">{workspaceLabel(activeOrg)}</span>
        {canSwitch ? <ChevronDown className="h-4 w-4 opacity-60" /> : null}
      </Button>

      {open && canSwitch ? (
        <>
          <button
            type="button"
            className="fixed inset-0 z-40 cursor-default"
            aria-label="Close workspace menu"
            onClick={() => setOpen(false)}
          />
          <div className="absolute right-0 top-full z-50 mt-2 min-w-[240px] rounded-lg border bg-popover p-1.5 text-popover-foreground shadow-overlay">
            <p className="px-2 py-1 text-caption font-medium text-muted-foreground">
              Switch workspace
            </p>
            {orgs.map((org) => (
              <button
                key={org.id}
                type="button"
                className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-small transition-colors duration-micro hover:bg-accent hover:text-accent-foreground"
                onClick={() => void handleSwitch(org.id)}
              >
                <span>{workspaceLabel(org)}</span>
                {org.id === activeOrg.id ? (
                  <Badge variant="outline" className="text-[10px]">
                    Active
                  </Badge>
                ) : null}
              </button>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
