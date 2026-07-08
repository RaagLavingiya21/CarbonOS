-- Scope 2 ("Grid") — record EAC-covered (renewable) MWh on a calculation. Range 040-049.
--
-- The dual-method engine already computes how much load quality-passing EACs cover
-- per site; persisting the total lets disclosures report the ESRS E1-5 renewable
-- share without re-screening instruments. Additive column, nullable for old rows.
--
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

ALTER TABLE s2_calculations
    ADD COLUMN IF NOT EXISTS renewable_mwh DOUBLE PRECISION;
