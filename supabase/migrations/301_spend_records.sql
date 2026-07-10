-- Scope 3 · Epic A · normalized GL/ERP spend lines feeding an inventory version.
-- org_id is carried (denormalized) on every table so RLS is a direct
-- public.is_org_member(org_id) check with no joins.

CREATE TABLE IF NOT EXISTS s3_spend_records (
    spend_record_id  BIGSERIAL PRIMARY KEY,
    inventory_id     BIGINT NOT NULL REFERENCES s3_inventory_versions (inventory_id) ON DELETE CASCADE,
    org_id           UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id          UUID REFERENCES auth.users (id),   -- created_by metadata only
    gl_account       TEXT,
    description      TEXT,
    vendor           TEXT,
    amount_usd       DOUBLE PRECISION,
    currency         TEXT DEFAULT 'USD',
    period           TEXT,
    source_file      TEXT,
    flag_status      TEXT NOT NULL DEFAULT 'ok',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_spend_records_org ON s3_spend_records (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_spend_records_inventory ON s3_spend_records (inventory_id);

ALTER TABLE s3_spend_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_spend_records_select ON s3_spend_records;
CREATE POLICY s3_spend_records_select ON s3_spend_records
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_records_insert ON s3_spend_records;
CREATE POLICY s3_spend_records_insert ON s3_spend_records
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_records_update ON s3_spend_records;
CREATE POLICY s3_spend_records_update ON s3_spend_records
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_records_delete ON s3_spend_records;
CREATE POLICY s3_spend_records_delete ON s3_spend_records
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
