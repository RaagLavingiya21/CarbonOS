-- Scope 2 ("Grid") — dual-method calculation results (PRD 5.4). Range 040-049.
--
-- VERSIONED / IMMUTABLE (PRD 5.6, mirrors the platform's published-footprint rule):
-- a recalculation INSERTs a new calc_id; an existing row is never updated. There is
-- deliberately NO UPDATE policy, so RLS denies updates at the database level — a
-- persisted calculation can never silently change. The two totals are stored in
-- separate columns and never merged.
--
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

CREATE TABLE IF NOT EXISTS s2_calculations (
    calc_id                 BIGSERIAL PRIMARY KEY,
    org_id                  UUID NOT NULL,
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    reporting_year          INTEGER NOT NULL,
    scope                   TEXT NOT NULL DEFAULT 'entity'
        CHECK (scope IN ('site','entity')),
    site_id                 BIGINT REFERENCES s2_sites(site_id) ON DELETE SET NULL,
    location_based_kg_co2e  DOUBLE PRECISION NOT NULL,
    market_based_kg_co2e    DOUBLE PRECISION NOT NULL,
    consumption_mwh         DOUBLE PRECISION,
    market_tier             TEXT,
    market_fallback_flagged BOOLEAN NOT NULL DEFAULT false,
    factor_versions         JSONB,   -- {factor_type/region: vintage_year} used
    inputs_hash             TEXT,     -- hash of inputs for reproducibility
    methodology_notes       TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by              UUID
);

CREATE INDEX IF NOT EXISTS idx_s2_calc_org_year ON s2_calculations (org_id, reporting_year);
CREATE INDEX IF NOT EXISTS idx_s2_calc_site ON s2_calculations (site_id);

ALTER TABLE s2_calculations ENABLE ROW LEVEL SECURITY;

CREATE POLICY s2_calc_select_org ON s2_calculations
    FOR SELECT TO authenticated USING (public.shares_org_with(user_id));
CREATE POLICY s2_calc_insert_self ON s2_calculations
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
-- No UPDATE policy on purpose (immutability). DELETE allowed for draft cleanup.
CREATE POLICY s2_calc_delete_org ON s2_calculations
    FOR DELETE TO authenticated USING (public.shares_org_with(user_id));
