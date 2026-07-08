-- Scope 1 — Bayou Energy integration credentials (org-level).
--
-- Stores per-org Bayou API keys (credential-connect pattern). Allows each
-- organization to connect their own Bayou account to auto-fetch + parse
-- utility bills (PDFs) in the background.
--
-- A single row per org, org-admin-editable. Encrypted at-rest by Supabase
-- (via DATABASE_URL encryption). The API key is never exposed to the frontend.
--
-- Band: Scope 1 = 110–199.

DROP POLICY IF EXISTS s1_bayou_credentials_select ON s1_bayou_credentials;
DROP POLICY IF EXISTS s1_bayou_credentials_update ON s1_bayou_credentials;
DROP POLICY IF EXISTS s1_bayou_credentials_delete ON s1_bayou_credentials;
DROP TABLE IF EXISTS s1_bayou_credentials;

CREATE TABLE IF NOT EXISTS s1_bayou_credentials (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL UNIQUE REFERENCES organizations (id) ON DELETE CASCADE,
    bayou_api_key  TEXT NOT NULL,                           -- encrypted at-rest by Supabase
    is_active      BOOLEAN NOT NULL DEFAULT true,           -- can be deactivated without deleting
    last_sync      TIMESTAMPTZ,                             -- last successful bill fetch
    next_sync      TIMESTAMPTZ,                             -- next scheduled sync
    sync_interval  INTERVAL DEFAULT '1 hour'::interval,    -- poll frequency
    created_by     UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_bayou_credentials_org_id ON s1_bayou_credentials (org_id);

-- RLS: org-admin-only reads/writes (via is_org_member check)
ALTER TABLE s1_bayou_credentials ENABLE ROW LEVEL SECURITY;

CREATE POLICY s1_bayou_credentials_select ON s1_bayou_credentials
    FOR SELECT
    USING (public.is_org_member(org_id));

CREATE POLICY s1_bayou_credentials_update ON s1_bayou_credentials
    FOR UPDATE
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

CREATE POLICY s1_bayou_credentials_delete ON s1_bayou_credentials
    FOR DELETE
    USING (public.is_org_member(org_id));

COMMENT ON TABLE s1_bayou_credentials IS 'Org-level Bayou Energy API credentials for bill auto-fetch.';
COMMENT ON COLUMN s1_bayou_credentials.bayou_api_key IS 'Bayou API key (encrypted at-rest); never exposed to frontend.';
COMMENT ON COLUMN s1_bayou_credentials.sync_interval IS 'Poll frequency for background bill sync.';
