-- Scope 1 module: per-org role (admin/editor/viewer) layered on org membership.
-- The shared org_members table only has admin/member; per hygiene rule #5 we do
-- NOT extend it. This s1_-owned table refines Scope-1 write access for members
-- of an org. Absence of a row means the app-layer default applies (org admin ->
-- Scope-1 admin, else editor). RLS enforces org tenancy only (is_org_member);
-- admin-only writes are enforced in the route layer.

CREATE TABLE IF NOT EXISTS s1_member_role (
    org_id     UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id    UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    role       TEXT NOT NULL DEFAULT 'editor',      -- admin | editor | viewer
    updated_by UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (org_id, user_id),
    CONSTRAINT s1_member_role_chk CHECK (role IN ('admin', 'editor', 'viewer'))
);

CREATE INDEX IF NOT EXISTS idx_s1_member_role_org ON s1_member_role (org_id);

ALTER TABLE s1_member_role ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s1_member_role_select_org ON s1_member_role;
CREATE POLICY s1_member_role_select_org ON s1_member_role
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_member_role_insert_org ON s1_member_role;
CREATE POLICY s1_member_role_insert_org ON s1_member_role
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_member_role_update_org ON s1_member_role;
CREATE POLICY s1_member_role_update_org ON s1_member_role
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_member_role_delete_org ON s1_member_role;
CREATE POLICY s1_member_role_delete_org ON s1_member_role
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));
