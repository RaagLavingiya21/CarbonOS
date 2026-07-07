-- Scope 2 ("Grid") — EAC / contractual-instrument registry (PRD 5.4; V1). Range 040-049.
--
-- Records the RECs / GOs / green tariffs / PPAs that back market-based accounting.
-- The 6 storable GHG Protocol quality-evidence flags live here; the remaining two
-- criteria (same_market, vintage_matched) are DERIVED at calc time against the
-- consuming site's region and the reporting year, so they are not stored.
--
-- ISOLATION: intra-module FK to s2_sites only. No FK to any Carbon OS table.
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

CREATE TABLE IF NOT EXISTS s2_eac_instruments (
    instrument_id   BIGSERIAL PRIMARY KEY,
    site_id         BIGINT NOT NULL REFERENCES s2_sites(site_id) ON DELETE CASCADE,
    org_id          UUID NOT NULL,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    instrument_type TEXT NOT NULL DEFAULT 'rec'
        CHECK (instrument_type IN ('rec','go','green_tariff','ppa')),
    reporting_year  INT NOT NULL,
    mwh             DOUBLE PRECISION NOT NULL,
    region_market   TEXT NOT NULL,           -- eGRID subregion / country the EAC is issued in
    vintage_year    INT NOT NULL,
    kg_co2e_per_mwh DOUBLE PRECISION NOT NULL DEFAULT 0.0,  -- unbundled RECs convey 0
    -- GHG Protocol Scope 2 quality evidence (same_market + vintage derived at calc time).
    specific_generation_attribute BOOLEAN NOT NULL DEFAULT true,
    unique_no_double_count        BOOLEAN NOT NULL DEFAULT true,
    registry_tracked              BOOLEAN NOT NULL DEFAULT true,
    retired_for_buyer             BOOLEAN NOT NULL DEFAULT true,
    not_an_offset                 BOOLEAN NOT NULL DEFAULT true,
    transparent                   BOOLEAN NOT NULL DEFAULT true,
    -- Provenance for assurance.
    registry_name   TEXT,                     -- e.g. 'M-RETS', 'WREGIS', 'APX', 'AIB'
    retirement_id   TEXT,                     -- registry retirement / cancellation id
    retirement_date DATE,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s2_eac_site ON s2_eac_instruments (site_id);
CREATE INDEX IF NOT EXISTS idx_s2_eac_org ON s2_eac_instruments (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_eac_year ON s2_eac_instruments (reporting_year);

ALTER TABLE s2_eac_instruments ENABLE ROW LEVEL SECURITY;

-- Org-collaborative read/write; insert as the acting user.
-- Idempotent (safe to re-run): DROP POLICY IF EXISTS precedes each CREATE POLICY.
DROP POLICY IF EXISTS s2_eac_select_org ON s2_eac_instruments;
CREATE POLICY s2_eac_select_org ON s2_eac_instruments
    FOR SELECT TO authenticated USING (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_eac_insert_self ON s2_eac_instruments;
CREATE POLICY s2_eac_insert_self ON s2_eac_instruments
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS s2_eac_update_org ON s2_eac_instruments;
CREATE POLICY s2_eac_update_org ON s2_eac_instruments
    FOR UPDATE TO authenticated USING (public.shares_org_with(user_id))
    WITH CHECK (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_eac_delete_org ON s2_eac_instruments;
CREATE POLICY s2_eac_delete_org ON s2_eac_instruments
    FOR DELETE TO authenticated USING (public.shares_org_with(user_id));
