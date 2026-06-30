-- Allow org_members upsert (ON CONFLICT DO UPDATE) for existing members.

CREATE POLICY org_members_update_member ON org_members
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));
