-- Scope 3 · Epic H · captured per-SKU use-phase specs (energy/water + use
-- profile) for Category 11 calculation. Band 310+.

CREATE TABLE IF NOT EXISTS s3_use_phase_specs (
    spec_id            BIGSERIAL PRIMARY KEY,
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id            UUID REFERENCES auth.users (id),   -- created_by metadata only
    product_ref        TEXT NOT NULL,
    energy_per_use_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    water_l_per_use    DOUBLE PRECISION NOT NULL DEFAULT 0,
    standby_power_w    DOUBLE PRECISION NOT NULL DEFAULT 0,
    fuel_kwh_per_use   DOUBLE PRECISION NOT NULL DEFAULT 0,
    spec_source        TEXT,
    uses_per_year      DOUBLE PRECISION NOT NULL DEFAULT 0,
    lifetime_years     DOUBLE PRECISION NOT NULL DEFAULT 0,
    sub_sector         TEXT,
    units_sold         DOUBLE PRECISION NOT NULL DEFAULT 0,
    region             TEXT,
    mode               TEXT NOT NULL DEFAULT 'direct' CHECK (mode IN ('direct', 'indirect')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_use_phase_specs_org ON s3_use_phase_specs (org_id);

ALTER TABLE s3_use_phase_specs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_use_phase_specs_select ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_select ON s3_use_phase_specs
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_use_phase_specs_insert ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_insert ON s3_use_phase_specs
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_use_phase_specs_update ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_update ON s3_use_phase_specs
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_use_phase_specs_delete ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_delete ON s3_use_phase_specs
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
