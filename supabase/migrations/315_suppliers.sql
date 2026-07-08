-- Scope 3 · Epic F · suppliers for cohorting + program scorecards. Band 310+.

CREATE TABLE IF NOT EXISTS s3_suppliers (
    supplier_id          BIGSERIAL PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id              UUID REFERENCES auth.users (id),   -- created_by metadata only
    name                 TEXT NOT NULL,
    scope3_category      SMALLINT NOT NULL CHECK (scope3_category BETWEEN 1 AND 15),
    emissions_kg         DOUBLE PRECISION NOT NULL DEFAULT 0,
    spend_usd            DOUBLE PRECISION NOT NULL DEFAULT 0,
    pcf_received         BOOLEAN NOT NULL DEFAULT false,
    dq_score             DOUBLE PRECISION,
    supplier_sbt_status  TEXT NOT NULL DEFAULT 'none'
                         CHECK (supplier_sbt_status IN ('none', 'committed', 'validated')),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_suppliers_org ON s3_suppliers (org_id);

ALTER TABLE s3_suppliers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_suppliers_select ON s3_suppliers;
CREATE POLICY s3_suppliers_select ON s3_suppliers
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_suppliers_insert ON s3_suppliers;
CREATE POLICY s3_suppliers_insert ON s3_suppliers
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_suppliers_update ON s3_suppliers;
CREATE POLICY s3_suppliers_update ON s3_suppliers
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_suppliers_delete ON s3_suppliers;
CREATE POLICY s3_suppliers_delete ON s3_suppliers
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
