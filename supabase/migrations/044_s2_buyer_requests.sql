-- Scope 2 ("Grid") — inbound buyer/CDP request queue (PRD 5.5). Range 040-049.
--
-- Track multiple inbound requests (Walmart, Amazon, CDP, EcoVadis, ...) with
-- deadlines and status, and link the calculation used to answer each. Intra-module
-- FK to s2_calculations only; no Carbon OS coupling.
--
-- Idempotent (safe to re-run). APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md).

CREATE TABLE IF NOT EXISTS s2_buyer_requests (
    request_id     BIGSERIAL PRIMARY KEY,
    org_id         UUID NOT NULL,
    user_id        UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    buyer_name     TEXT NOT NULL,
    destination    TEXT NOT NULL DEFAULT 'standard'
        CHECK (destination IN ('standard','cdp','amazon')),
    reporting_year INTEGER,
    due_date       DATE,
    status         TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open','answered','declined')),
    calc_id        BIGINT REFERENCES s2_calculations(calc_id) ON DELETE SET NULL,
    answered_at    TIMESTAMPTZ,
    notes          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s2_buyer_org ON s2_buyer_requests (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_buyer_status ON s2_buyer_requests (status);
CREATE INDEX IF NOT EXISTS idx_s2_buyer_due ON s2_buyer_requests (due_date);

ALTER TABLE s2_buyer_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s2_buyer_select_org ON s2_buyer_requests;
CREATE POLICY s2_buyer_select_org ON s2_buyer_requests
    FOR SELECT TO authenticated USING (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_buyer_insert_self ON s2_buyer_requests;
CREATE POLICY s2_buyer_insert_self ON s2_buyer_requests
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS s2_buyer_update_org ON s2_buyer_requests;
CREATE POLICY s2_buyer_update_org ON s2_buyer_requests
    FOR UPDATE TO authenticated USING (public.shares_org_with(user_id))
    WITH CHECK (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_buyer_delete_org ON s2_buyer_requests;
CREATE POLICY s2_buyer_delete_org ON s2_buyer_requests
    FOR DELETE TO authenticated USING (public.shares_org_with(user_id));
