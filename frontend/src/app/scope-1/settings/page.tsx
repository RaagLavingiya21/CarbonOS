"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Users } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { scope1Api, type S1Member } from "@/lib/scope1-api";

const ROLES = ["admin", "editor", "viewer"];

function roleVariant(role: string): "default" | "info" | "neutral" {
  if (role === "admin") return "default";
  if (role === "editor") return "info";
  return "neutral";
}

function RoleSelect({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (role: string) => void;
  disabled?: boolean;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      disabled={disabled}
      className="h-8 rounded-md border bg-card px-2 text-small disabled:opacity-50"
    >
      {ROLES.map((role) => (
        <option key={role} value={role}>
          {role}
        </option>
      ))}
    </select>
  );
}

export default function Scope1SettingsPage() {
  const [members, setMembers] = useState<S1Member[]>([]);
  const [yourRole, setYourRole] = useState<string>("viewer");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await scope1Api.listMembers();
      setMembers(data.members);
      setYourRole(data.your_role);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const isAdmin = yourRole === "admin";

  async function changeRole(memberId: string, role: string) {
    try {
      await scope1Api.setMemberRole(memberId, role);
      await load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" className="-ml-3">
        <Link href="/scope-1">
          <ArrowLeft className="h-4 w-4" />
          Back to Scope 1
        </Link>
      </Button>

      <div>
        <div className="flex items-center gap-2">
          <Users className="h-6 w-6 text-muted-foreground" />
          <h1 className="text-h1">Team & roles</h1>
        </div>
        <p className="mt-2 text-small text-muted-foreground">
          Admins manage roles. Editors can enter and edit data; viewers are read-only.
          {!isAdmin ? " You have read-only access to this page." : ""}
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {isAdmin ? <InviteCard onInvited={load} onError={setError} /> : null}

      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
          <CardDescription>Your Scope 1 role: <span className="font-medium">{yourRole}</span></CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-small text-muted-foreground">Loading…</p>
          ) : (
            <div className="overflow-x-auto rounded-lg border">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="bg-secondary text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">User</th>
                    <th className="px-3 py-2">Role</th>
                    {isAdmin ? <th className="px-3 py-2">Change</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {members.map((member) => (
                    <tr key={member.user_id} className="border-t bg-card">
                      <td className="px-3 py-2 font-mono text-caption">
                        {member.user_id.slice(0, 8)}…
                        {member.is_you ? <span className="ml-2 text-muted-foreground">(you)</span> : null}
                      </td>
                      <td className="px-3 py-2">
                        <Badge variant={roleVariant(member.role)}>{member.role}</Badge>
                        {!member.explicit ? (
                          <span className="ml-2 text-caption text-muted-foreground">default</span>
                        ) : null}
                      </td>
                      {isAdmin ? (
                        <td className="px-3 py-2">
                          <RoleSelect
                            value={member.role}
                            disabled={member.is_you}
                            onChange={(role) => changeRole(member.user_id, role)}
                          />
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function InviteCard({
  onInvited,
  onError,
}: {
  onInvited: () => void;
  onError: (message: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("editor");
  const [saving, setSaving] = useState(false);

  async function submit() {
    if (!email.trim()) return;
    setSaving(true);
    try {
      await scope1Api.inviteMember(email.trim(), role);
      setEmail("");
      onInvited();
    } catch (err) {
      onError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Invite a member</CardTitle>
        <CardDescription>They must already have a platform account.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-56 flex-1 space-y-1.5">
            <Label>Email</Label>
            <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="teammate@company.com" />
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <RoleSelect value={role} onChange={setRole} />
          </div>
          <Button type="button" onClick={submit} disabled={saving || !email.trim()}>
            Invite
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
