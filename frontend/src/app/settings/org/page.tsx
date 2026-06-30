"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Building2, UserMinus, UserPlus } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  OrgDetail,
  OrgMember,
  addMember,
  createOrg,
  getMyOrg,
  removeMember,
  workspaceLabel,
} from "@/lib/org-api";
import { createSupabaseBrowserClient } from "@/lib/supabase";

export default function OrgSettingsPage() {
  const supabase = useMemo(() => createSupabaseBrowserClient(), []);
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [orgDetail, setOrgDetail] = useState<OrgDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [orgName, setOrgName] = useState("");
  const [memberEmail, setMemberEmail] = useState("");

  const loadOrg = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await getMyOrg();
      setOrgDetail(detail);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setCurrentUserId(data.session?.user.id ?? null);
    });
    void loadOrg();
  }, [loadOrg, supabase]);

  async function handleCreateOrg(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting("create");
    setError(null);
    try {
      await createOrg(orgName.trim());
      setOrgName("");
      await loadOrg();
      window.dispatchEvent(new CustomEvent("workspace-changed"));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(null);
    }
  }

  async function handleAddMember(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!orgDetail?.active_org) return;
    setSubmitting("add");
    setError(null);
    try {
      await addMember(orgDetail.active_org.id, memberEmail.trim());
      setMemberEmail("");
      await loadOrg();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(null);
    }
  }

  async function handleRemoveMember(member: OrgMember) {
    if (!orgDetail?.active_org) return;
    setSubmitting(`remove-${member.user_id}`);
    setError(null);
    try {
      await removeMember(orgDetail.active_org.id, member.user_id);
      await loadOrg();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(null);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl">
        <p className="text-sm text-muted-foreground">Loading organization...</p>
      </div>
    );
  }

  const activeOrg = orgDetail?.active_org;
  const members = orgDetail?.members ?? [];
  const hasPersonalOrg = orgDetail?.orgs.some((org) => !org.is_demo) ?? false;
  const isDemoActive = activeOrg?.is_demo ?? false;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Organization</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage your team and shared workspace access.
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {isDemoActive ? (
        <Alert>
          <AlertDescription>
            You are in the shared demo workspace with sample data. Create your own
            organization when you are ready to start fresh with your team.
          </AlertDescription>
        </Alert>
      ) : null}

      {!hasPersonalOrg ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5" />
              Create your organization
            </CardTitle>
            <CardDescription>
              Start a private workspace for your team. You will keep access to the demo
              workspace and can switch between them from the top bar.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateOrg} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="org-name">Organization name</Label>
                <Input
                  id="org-name"
                  value={orgName}
                  onChange={(event) => setOrgName(event.target.value)}
                  placeholder="Acme Corp"
                  required
                />
              </div>
              <Button type="submit" disabled={submitting === "create" || !orgName.trim()}>
                {submitting === "create" ? "Creating..." : "Create my organization"}
              </Button>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {activeOrg ? (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                {workspaceLabel(activeOrg)}
              </CardTitle>
              <CardDescription>
                {members.length} team member{members.length === 1 ? "" : "s"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-hidden rounded-lg border">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50 text-left">
                      <th className="px-4 py-3 font-medium">User ID</th>
                      <th className="px-4 py-3 font-medium">Role</th>
                      {!isDemoActive ? (
                        <th className="px-4 py-3 font-medium text-right">Actions</th>
                      ) : null}
                    </tr>
                  </thead>
                  <tbody>
                    {members.map((member) => {
                      const isSelf = member.user_id === currentUserId;
                      return (
                        <tr key={member.user_id} className="border-b last:border-b-0">
                          <td className="px-4 py-3 font-mono text-xs">
                            {member.user_id.slice(0, 8)}...
                            {isSelf ? (
                              <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                                you
                              </span>
                            ) : null}
                          </td>
                          <td className="px-4 py-3 capitalize">{member.role}</td>
                          {!isDemoActive ? (
                            <td className="px-4 py-3 text-right">
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={
                                  submitting === `remove-${member.user_id}` || isSelf
                                }
                                onClick={() => void handleRemoveMember(member)}
                              >
                                <UserMinus className="mr-1 h-4 w-4" />
                                Remove
                              </Button>
                            </td>
                          ) : null}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {!isDemoActive ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <UserPlus className="h-5 w-5" />
                  Add member
                </CardTitle>
                <CardDescription>
                  Invite a teammate by their account email. They must already have signed up.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleAddMember} className="flex flex-col gap-4 sm:flex-row">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor="member-email" className="sr-only">
                      Email
                    </Label>
                    <Input
                      id="member-email"
                      type="email"
                      value={memberEmail}
                      onChange={(event) => setMemberEmail(event.target.value)}
                      placeholder="colleague@company.com"
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={submitting === "add" || !memberEmail.trim()}
                    className="sm:self-end"
                  >
                    {submitting === "add" ? "Adding..." : "Add member"}
                  </Button>
                </form>
              </CardContent>
            </Card>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
