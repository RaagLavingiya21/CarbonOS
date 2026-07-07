-- Scope 2 ("Grid") module — site master (PRD 5.3; SCOPE2_IMPLEMENTATION_PLAN.md Section 3).
--
-- MIGRATION RANGE: Scope 2 uses 040-049. Scope 1 reserves 030-039
-- (feature/scope1-mvp-phase1 ships 030_s1_* .. 036_s1_rls). Keep Scope 2 >= 040
-- so the two modules never collide on migration numbers at merge time.
--
-- ISOLATION: this table belongs to the Scope 2 module. It has NO foreign keys to
-- any Carbon OS (Scope 3 / PACT) table. It reuses only the shared tenancy
-- primitives: auth.users, org_members, and the public.shares_org_with() helper
-- (defined in 017_org_data_visibility.sql, backed by org_members from
-- 010_create_organizations.sql).
--
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule) — never run untested against
-- the database holding demo data.

CREATE TABLE IF NOT EXISTS s2_sites (
    site_id               BIGSERIAL PRIMARY KEY,
    org_id                UUID NOT NULL,
    user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name                  TEXT NOT NULL,
    site_type             TEXT NOT NULL
        CHECK (site_type IN ('retail','grocery','food_service','manufacturing','warehouse_dc','office')),
    address               TEXT,
    zip                   TEXT,
    country               TEXT NOT NULL DEFAULT 'US',
    egrid_subregion       TEXT,
    iea_country           TEXT,
    ownership             TEXT NOT NULL DEFAULT 'tenant_metered'
        CHECK (ownership IN ('owned','tenant_metered','landlord_metered','sub_metered')),
    lease_type            TEXT NOT NULL DEFAULT 'nnn'
        CHECK (lease_type IN ('owned','gross','nnn','modified')),
    franchise_flag        BOOLEAN NOT NULL DEFAULT false,
    scope3_cat14_note     TEXT,  -- set when franchise_flag excludes the site from Scope 2
    consolidation_approach TEXT NOT NULL DEFAULT 'operational_control'
        CHECK (consolidation_approach IN ('operational_control','financial_control','equity_share')),
    status                TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active','inactive','seasonal')),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s2_sites_org ON s2_sites (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_sites_user ON s2_sites (user_id);
CREATE INDEX IF NOT EXISTS idx_s2_sites_egrid ON s2_sites (egrid_subregion);

-- Row-Level Security: org teammates can read/edit the org's sites (collaborative
-- data-wrangler persona); rows are inserted as the creating user.
ALTER TABLE s2_sites ENABLE ROW LEVEL SECURITY;

-- Idempotent (safe to re-run): DROP POLICY IF EXISTS precedes each CREATE POLICY.
DROP POLICY IF EXISTS s2_sites_select_org ON s2_sites;
CREATE POLICY s2_sites_select_org ON s2_sites
    FOR SELECT TO authenticated
    USING (public.shares_org_with(user_id));

DROP POLICY IF EXISTS s2_sites_insert_self ON s2_sites;
CREATE POLICY s2_sites_insert_self ON s2_sites
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS s2_sites_update_org ON s2_sites;
CREATE POLICY s2_sites_update_org ON s2_sites
    FOR UPDATE TO authenticated
    USING (public.shares_org_with(user_id))
    WITH CHECK (public.shares_org_with(user_id));

DROP POLICY IF EXISTS s2_sites_delete_org ON s2_sites;
CREATE POLICY s2_sites_delete_org ON s2_sites
    FOR DELETE TO authenticated
    USING (public.shares_org_with(user_id));
