-- Scope 2 ("Grid") — leased-site landlord data-request workflow (PRD 5.2). Range 040-049.
--
-- The wedge no incumbent fills: for landlord-metered leased sites, track a
-- templated data request to the landlord (status, reminders, structured intake) so
-- institutional knowledge persists across staff turnover. Intra-module FK to
-- s2_sites only; no Carbon OS coupling.
--
-- Idempotent (safe to re-run): DROP POLICY IF EXISTS precedes each CREATE POLICY.
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

CREATE TABLE IF NOT EXISTS s2_landlord_requests (
    request_id            BIGSERIAL PRIMARY KEY,
    site_id               BIGINT NOT NULL REFERENCES s2_sites(site_id) ON DELETE CASCADE,
    org_id                UUID NOT NULL,
    user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    landlord_contact      TEXT,
    method                TEXT NOT NULL DEFAULT 'email'
        CHECK (method IN ('email','portal','phone')),
    status                TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','sent','responded','declined','overdue')),
    sent_at               TIMESTAMPTZ,
    responded_at          TIMESTAMPTZ,
    reminder_cadence_days INTEGER NOT NULL DEFAULT 14,
    returned_data_ref     TEXT,
    notes                 TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s2_landlord_site ON s2_landlord_requests (site_id);
CREATE INDEX IF NOT EXISTS idx_s2_landlord_org ON s2_landlord_requests (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_landlord_status ON s2_landlord_requests (status);

ALTER TABLE s2_landlord_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s2_landlord_select_org ON s2_landlord_requests;
CREATE POLICY s2_landlord_select_org ON s2_landlord_requests
    FOR SELECT TO authenticated USING (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_landlord_insert_self ON s2_landlord_requests;
CREATE POLICY s2_landlord_insert_self ON s2_landlord_requests
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS s2_landlord_update_org ON s2_landlord_requests;
CREATE POLICY s2_landlord_update_org ON s2_landlord_requests
    FOR UPDATE TO authenticated USING (public.shares_org_with(user_id))
    WITH CHECK (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_landlord_delete_org ON s2_landlord_requests;
CREATE POLICY s2_landlord_delete_org ON s2_landlord_requests
    FOR DELETE TO authenticated USING (public.shares_org_with(user_id));
