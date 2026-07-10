-- Scope 3 · Epic A · corporate inventory version (snapshot of a company's
-- Scope 3 inventory for a reporting year). Band 050-059 (Scope 3 lane).
-- Tenancy: org_id is the RLS key via public.is_org_member(org_id) (migration 014).
-- user_id is created_by metadata only and is NEVER referenced in a policy.

CREATE TABLE IF NOT EXISTS s3_inventory_versions (
    inventory_id       BIGSERIAL PRIMARY KEY,
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id            UUID REFERENCES auth.users (id),   -- created_by metadata only
    reporting_year     INTEGER NOT NULL,
    boundary_approach  TEXT NOT NULL DEFAULT 'operational_control'
                       CHECK (boundary_approach IN ('equity', 'financial_control', 'operational_control')),
    status             TEXT NOT NULL DEFAULT 'draft'
                       CHECK (status IN ('draft', 'calculated', 'locked')),
    is_base_year       BOOLEAN NOT NULL DEFAULT false,
    total_kg_co2e      DOUBLE PRECISION,
    version            INTEGER NOT NULL DEFAULT 1,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_s3_inventory_versions_org ON s3_inventory_versions (org_id);

ALTER TABLE s3_inventory_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_inventory_versions_select ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_select ON s3_inventory_versions
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_versions_insert ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_insert ON s3_inventory_versions
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_versions_update ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_update ON s3_inventory_versions
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_versions_delete ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_delete ON s3_inventory_versions
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
