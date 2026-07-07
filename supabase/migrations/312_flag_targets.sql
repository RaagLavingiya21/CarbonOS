-- Scope 3 · Epic D · FLAG (Forest, Land & Agriculture) target attached to a
-- target when the company is FLAG-designated or FLAG >=20% of total.

CREATE TABLE IF NOT EXISTS s3_flag_targets (
    id                              BIGSERIAL PRIMARY KEY,
    target_id                       BIGINT NOT NULL REFERENCES s3_targets (target_id) ON DELETE CASCADE,
    org_id                          UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    flag_share_pct                  DOUBLE PRECISION,
    flag_target_type                TEXT,
    no_deforestation_commitment_date DATE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (target_id)
);

CREATE INDEX IF NOT EXISTS idx_s3_flag_targets_org ON s3_flag_targets (org_id);

ALTER TABLE s3_flag_targets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_flag_targets_select ON s3_flag_targets;
CREATE POLICY s3_flag_targets_select ON s3_flag_targets
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_flag_targets_insert ON s3_flag_targets;
CREATE POLICY s3_flag_targets_insert ON s3_flag_targets
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_flag_targets_update ON s3_flag_targets;
CREATE POLICY s3_flag_targets_update ON s3_flag_targets
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_flag_targets_delete ON s3_flag_targets;
CREATE POLICY s3_flag_targets_delete ON s3_flag_targets
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
