-- Scope 3 · Epic E · recorded base-year recalculation decisions (GHG Protocol
-- significance-threshold policy).

CREATE TABLE IF NOT EXISTS s3_base_year_recalcs (
    recalc_id        BIGSERIAL PRIMARY KEY,
    org_id           UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id          UUID REFERENCES auth.users (id),   -- created_by metadata only
    trigger          TEXT NOT NULL,
    significance_pct DOUBLE PRECISION,
    threshold_pct    DOUBLE PRECISION,
    recalc_required  BOOLEAN NOT NULL DEFAULT false,
    rationale        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_base_year_recalcs_org ON s3_base_year_recalcs (org_id);

ALTER TABLE s3_base_year_recalcs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_base_year_recalcs_select ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_select ON s3_base_year_recalcs
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_base_year_recalcs_insert ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_insert ON s3_base_year_recalcs
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_base_year_recalcs_update ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_update ON s3_base_year_recalcs
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_base_year_recalcs_delete ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_delete ON s3_base_year_recalcs
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
