-- Scope 3 · Epic I · recorded green-claim assessments (substantiation + dated
-- compliance flags). Levers + MAC are stateless compute; only claims persist.

CREATE TABLE IF NOT EXISTS s3_claims (
    claim_id              BIGSERIAL PRIMARY KEY,
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id               UUID REFERENCES auth.users (id),   -- created_by metadata only
    claim_text            TEXT NOT NULL,
    jurisdiction          TEXT NOT NULL,
    substantiable         BOOLEAN NOT NULL DEFAULT false,
    substantiation_reason TEXT,
    ruleset_version       TEXT NOT NULL,
    flags                 JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_claims_org ON s3_claims (org_id);

ALTER TABLE s3_claims ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_claims_select ON s3_claims;
CREATE POLICY s3_claims_select ON s3_claims
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_claims_insert ON s3_claims;
CREATE POLICY s3_claims_insert ON s3_claims
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_claims_update ON s3_claims;
CREATE POLICY s3_claims_update ON s3_claims
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_claims_delete ON s3_claims;
CREATE POLICY s3_claims_delete ON s3_claims
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
