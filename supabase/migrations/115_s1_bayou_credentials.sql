-- Scope 1 — Bayou Energy integration credentials (org-level, credential-connect).
--
-- Stores a per-org Bayou API key so the backend can auto-fetch + parse utility
-- bills (PDFs) in the background. One row per org.
--
-- SECURITY (revised): this table is **backend / service-role ONLY**. RLS is
-- enabled with NO policies for the anon/authenticated roles, so the frontend
-- anon key (any org member's JWT) cannot read/write it — the raw `bayou_api_key`
-- is never exposed to a client. The service-role backend bypasses RLS; all
-- access flows through `/api/scope1/bayou-credentials`, which gates writes to
-- org admins (app-layer) and never returns the key. (Column-level RLS can't hide
-- a single column, so deny-all + service-role is the correct way to keep the
-- secret un-readable by members.)
--
-- Idempotent: no DROP TABLE (that would wipe stored credentials on re-run);
-- CREATE ... IF NOT EXISTS + DROP POLICY IF EXISTS guards make it re-runnable.
--
-- Band: Scope 1 = 110–199.

CREATE TABLE IF NOT EXISTS s1_bayou_credentials (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL UNIQUE REFERENCES organizations (id) ON DELETE CASCADE,
    bayou_api_key  TEXT NOT NULL,                           -- backend/service-role only
    is_active      BOOLEAN NOT NULL DEFAULT true,           -- deactivate without deleting
    last_sync      TIMESTAMPTZ,                             -- last successful bill fetch
    next_sync      TIMESTAMPTZ,                             -- next scheduled sync
    sync_interval  INTERVAL DEFAULT '1 hour'::interval,     -- poll frequency
    created_by     UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_bayou_credentials_org_id ON s1_bayou_credentials (org_id);

-- Deny-by-default: RLS on, no anon/authenticated policies -> only the service
-- role (backend) can touch this table. Drop any prior member-facing policies
-- (an earlier revision exposed the key to all org members via is_org_member).
ALTER TABLE s1_bayou_credentials ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_bayou_credentials_select ON s1_bayou_credentials;
DROP POLICY IF EXISTS s1_bayou_credentials_insert ON s1_bayou_credentials;
DROP POLICY IF EXISTS s1_bayou_credentials_update ON s1_bayou_credentials;
DROP POLICY IF EXISTS s1_bayou_credentials_delete ON s1_bayou_credentials;

COMMENT ON TABLE s1_bayou_credentials IS 'Org-level Bayou API credentials for bill auto-fetch. Backend/service-role only; RLS denies all client access.';
COMMENT ON COLUMN s1_bayou_credentials.bayou_api_key IS 'Bayou API key. Backend/service-role only; never returned to a client.';
