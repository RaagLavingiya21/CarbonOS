-- Scope 3 · Epic B · inbound questionnaire requests (a customer/retailer/CDP/
-- EcoVadis questionnaire to answer). Band 050-059. org_id RLS via is_org_member.

CREATE TABLE IF NOT EXISTS s3_questionnaire_requests (
    request_id      BIGSERIAL PRIMARY KEY,
    org_id          UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id         UUID REFERENCES auth.users (id),   -- created_by metadata only
    customer_name   TEXT,
    framework       TEXT NOT NULL DEFAULT 'generic'
                    CHECK (framework IN ('cdp', 'ecovadis', 'walmart', 'tesco_cdf', 'generic')),
    source_file     TEXT,
    deadline        DATE,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_progress', 'submitted', 'declined')),
    inventory_id    BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_questionnaire_requests_org ON s3_questionnaire_requests (org_id);

ALTER TABLE s3_questionnaire_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_questionnaire_requests_select ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_select ON s3_questionnaire_requests
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_requests_insert ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_insert ON s3_questionnaire_requests
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_requests_update ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_update ON s3_questionnaire_requests
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_requests_delete ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_delete ON s3_questionnaire_requests
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
