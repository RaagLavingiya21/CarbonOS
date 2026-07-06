-- Scope 3 · Epic A · classifier output per spend line (separate table so
-- re-classification is versionable and analyst overrides are auditable).

CREATE TABLE IF NOT EXISTS s3_spend_classifications (
    classification_id   BIGSERIAL PRIMARY KEY,
    spend_record_id     BIGINT NOT NULL REFERENCES s3_spend_records (spend_record_id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id             UUID REFERENCES auth.users (id),   -- created_by metadata only
    scope3_category     SMALLINT CHECK (scope3_category BETWEEN 1 AND 15),
    eeio_sector_code    TEXT,
    eeio_sector_name    TEXT,
    ef_kg_co2e_per_usd  DOUBLE PRECISION,
    kg_co2e             DOUBLE PRECISION,
    confidence_score    DOUBLE PRECISION,
    data_source         TEXT NOT NULL DEFAULT 'spend',
    is_override         BOOLEAN NOT NULL DEFAULT false,
    flag_status         TEXT NOT NULL DEFAULT 'ok',
    ef_source           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_spend_classifications_org ON s3_spend_classifications (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_spend_classifications_record ON s3_spend_classifications (spend_record_id);

ALTER TABLE s3_spend_classifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_spend_classifications_select ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_select ON s3_spend_classifications
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_classifications_insert ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_insert ON s3_spend_classifications
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_classifications_update ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_update ON s3_spend_classifications
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_classifications_delete ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_delete ON s3_spend_classifications
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
