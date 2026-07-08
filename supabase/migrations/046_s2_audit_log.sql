-- Scope 2 ("Grid") — immutable audit log (PRD 5.6). Range 040-049.
--
-- APPEND-ONLY: every reported tCO2e traces to a row here (source, factor
-- source/version, formula, intermediate values). There is deliberately NO UPDATE
-- and NO DELETE policy, so RLS makes the log tamper-evident at the database level.
--
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

CREATE TABLE IF NOT EXISTS s2_audit_log (
    audit_id            BIGSERIAL PRIMARY KEY,
    org_id              UUID NOT NULL,
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    calc_id             BIGINT REFERENCES s2_calculations(calc_id) ON DELETE CASCADE,
    entity_type         TEXT NOT NULL,  -- calculation | bill | site | instrument
    entity_id           BIGINT,
    source_ref          TEXT,
    factor_source       TEXT,
    factor_version      INTEGER,
    formula             TEXT,
    intermediate_values JSONB,
    actor               UUID,
    approval_status     TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s2_audit_org ON s2_audit_log (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_audit_calc ON s2_audit_log (calc_id);
CREATE INDEX IF NOT EXISTS idx_s2_audit_entity ON s2_audit_log (entity_type, entity_id);

ALTER TABLE s2_audit_log ENABLE ROW LEVEL SECURITY;

-- Read within org; insert as the acting user. No UPDATE/DELETE policy (immutable).
-- Idempotent (safe to re-run): DROP POLICY IF EXISTS precedes each CREATE POLICY.
DROP POLICY IF EXISTS s2_audit_select_org ON s2_audit_log;
CREATE POLICY s2_audit_select_org ON s2_audit_log
    FOR SELECT TO authenticated USING (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_audit_insert_self ON s2_audit_log;
CREATE POLICY s2_audit_insert_self ON s2_audit_log
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
