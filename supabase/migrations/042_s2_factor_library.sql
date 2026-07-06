-- Scope 2 ("Grid") — versioned grid emission-factor library (PRD 5.4). Range 040-049.
--
-- Global reference data (not org-scoped): eGRID subregions, IEA countries, Green-e
-- (US) & AIB (EU) residual mix, steam/heat. Every factor carries a source citation
-- (platform eval invariant). Seeded by scripts/seed_s2_factors.py via the service
-- role. Readable by all authenticated users; NOT writable by them (no write policy
-- => RLS denies writes; the service-role key bypasses RLS for seeding).
--
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

CREATE TABLE IF NOT EXISTS s2_factor_library (
    factor_id        BIGSERIAL PRIMARY KEY,
    factor_type      TEXT NOT NULL
        CHECK (factor_type IN ('egrid','iea','greene_residual','aib_residual','steam')),
    region_code      TEXT NOT NULL,
    vintage_year     INTEGER NOT NULL,
    publish_year     INTEGER,
    kg_co2e_per_mwh  DOUBLE PRECISION NOT NULL,
    gwp_set          TEXT NOT NULL DEFAULT 'AR6-GWP100',
    source_citation  TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (factor_type, region_code, vintage_year)
);

CREATE INDEX IF NOT EXISTS idx_s2_factors_lookup
    ON s2_factor_library (factor_type, region_code, vintage_year);

ALTER TABLE s2_factor_library ENABLE ROW LEVEL SECURITY;

-- Read-only to all authenticated users; writes only via service role (no policy).
CREATE POLICY s2_factors_select_all ON s2_factor_library
    FOR SELECT TO authenticated USING (true);
