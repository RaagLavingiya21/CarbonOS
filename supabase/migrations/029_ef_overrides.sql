-- Org-wide and personal emission-factor overrides (Wave 4 Workstream B).
-- Analyst corrections persist as material → sector mappings for future matches.

CREATE TABLE IF NOT EXISTS ef_overrides (
    override_id          BIGSERIAL PRIMARY KEY,
    org_id               UUID REFERENCES organizations (id) ON DELETE CASCADE,
    user_id              UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    material_normalized  TEXT NOT NULL,
    sector_code          TEXT NOT NULL,
    sector_name          TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (material_normalized = lower(trim(material_normalized)))
);

CREATE UNIQUE INDEX IF NOT EXISTS ef_overrides_org_material_uidx
    ON ef_overrides (org_id, material_normalized)
    WHERE org_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ef_overrides_user_material_uidx
    ON ef_overrides (user_id, material_normalized)
    WHERE org_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_ef_overrides_org_id ON ef_overrides (org_id);
CREATE INDEX IF NOT EXISTS idx_ef_overrides_user_id ON ef_overrides (user_id);

ALTER TABLE ef_overrides ENABLE ROW LEVEL SECURITY;

-- Read org-scoped overrides when caller is an org member.
CREATE POLICY ef_overrides_select_org ON ef_overrides
    FOR SELECT TO authenticated
    USING (
        org_id IS NOT NULL
        AND public.is_org_member(org_id)
    );

-- Read personal overrides owned by the caller.
CREATE POLICY ef_overrides_select_personal ON ef_overrides
    FOR SELECT TO authenticated
    USING (
        org_id IS NULL
        AND user_id = auth.uid()
    );

-- Insert org-scoped overrides when caller is an org member.
CREATE POLICY ef_overrides_insert_org ON ef_overrides
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id IS NOT NULL
        AND public.is_org_member(org_id)
        AND user_id = auth.uid()
    );

-- Insert personal overrides for the caller.
CREATE POLICY ef_overrides_insert_personal ON ef_overrides
    FOR INSERT TO authenticated
    WITH CHECK (
        org_id IS NULL
        AND user_id = auth.uid()
    );

-- Update org-scoped overrides when caller is an org member.
CREATE POLICY ef_overrides_update_org ON ef_overrides
    FOR UPDATE TO authenticated
    USING (
        org_id IS NOT NULL
        AND public.is_org_member(org_id)
    )
    WITH CHECK (
        org_id IS NOT NULL
        AND public.is_org_member(org_id)
        AND user_id = auth.uid()
    );

-- Update personal overrides owned by the caller.
CREATE POLICY ef_overrides_update_personal ON ef_overrides
    FOR UPDATE TO authenticated
    USING (
        org_id IS NULL
        AND user_id = auth.uid()
    )
    WITH CHECK (
        org_id IS NULL
        AND user_id = auth.uid()
    );

-- Delete org-scoped overrides when caller is an org member.
CREATE POLICY ef_overrides_delete_org ON ef_overrides
    FOR DELETE TO authenticated
    USING (
        org_id IS NOT NULL
        AND public.is_org_member(org_id)
    );

-- Delete personal overrides owned by the caller.
CREATE POLICY ef_overrides_delete_personal ON ef_overrides
    FOR DELETE TO authenticated
    USING (
        org_id IS NULL
        AND user_id = auth.uid()
    );
