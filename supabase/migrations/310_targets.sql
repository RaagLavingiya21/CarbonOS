-- Scope 3 · Epic D · SBTi targets. Band 310+ (Scope 3's second reserved block,
-- after 050-059). org_id RLS via public.is_org_member(org_id); user_id metadata.

CREATE TABLE IF NOT EXISTS s3_targets (
    target_id           BIGSERIAL PRIMARY KEY,
    org_id              UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id             UUID REFERENCES auth.users (id),   -- created_by metadata only
    type                TEXT NOT NULL DEFAULT 'near_term'
                        CHECK (type IN ('near_term', 'net_zero')),
    method              TEXT NOT NULL DEFAULT 'absolute'
                        CHECK (method IN ('absolute', 'intensity')),
    sbti_version        TEXT NOT NULL DEFAULT 'v2.0',
    base_year           INTEGER,
    target_year         INTEGER,
    reduction_pct       DOUBLE PRECISION,
    inventory_base_id   BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'ready', 'validated')),
    assurance_required  BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_targets_org ON s3_targets (org_id);

ALTER TABLE s3_targets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_targets_select ON s3_targets;
CREATE POLICY s3_targets_select ON s3_targets
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_targets_insert ON s3_targets;
CREATE POLICY s3_targets_insert ON s3_targets
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_targets_update ON s3_targets;
CREATE POLICY s3_targets_update ON s3_targets
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_targets_delete ON s3_targets;
CREATE POLICY s3_targets_delete ON s3_targets
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
