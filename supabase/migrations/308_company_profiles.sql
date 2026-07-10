-- Scope 3 · Epic C · persisted company profile that drives the obligation
-- engine (one per org). Band 050-059. org_id is the RLS key via
-- public.is_org_member(org_id); user_id is created_by metadata only.

CREATE TABLE IF NOT EXISTS s3_company_profiles (
    profile_id             BIGSERIAL PRIMARY KEY,
    org_id                 UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id                UUID REFERENCES auth.users (id),   -- created_by metadata only
    annual_revenue_usd     DOUBLE PRECISION,
    employee_count         INTEGER,
    is_us_entity           BOOLEAN NOT NULL DEFAULT false,
    does_business_in_ca    BOOLEAN NOT NULL DEFAULT false,
    eu_turnover_eur        DOUBLE PRECISION,
    eu_subsidiary          BOOLEAN NOT NULL DEFAULT false,
    eu_branch_turnover_eur DOUBLE PRECISION,
    listed_jurisdictions   JSONB NOT NULL DEFAULT '[]'::jsonb,
    sector                 TEXT,
    is_flag_sector         BOOLEAN NOT NULL DEFAULT false,
    key_customers          JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id)
);

CREATE INDEX IF NOT EXISTS idx_s3_company_profiles_org ON s3_company_profiles (org_id);

ALTER TABLE s3_company_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_company_profiles_select ON s3_company_profiles;
CREATE POLICY s3_company_profiles_select ON s3_company_profiles
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_company_profiles_insert ON s3_company_profiles;
CREATE POLICY s3_company_profiles_insert ON s3_company_profiles
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_company_profiles_update ON s3_company_profiles;
CREATE POLICY s3_company_profiles_update ON s3_company_profiles
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_company_profiles_delete ON s3_company_profiles;
CREATE POLICY s3_company_profiles_delete ON s3_company_profiles
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
