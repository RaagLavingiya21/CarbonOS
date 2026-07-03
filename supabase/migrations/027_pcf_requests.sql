-- PCF request inbox for Wave 2 Workstream R (Receive)

CREATE TABLE IF NOT EXISTS pcf_requests (
    request_id          BIGSERIAL PRIMARY KEY,
    org_id              UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    requester_name      TEXT,
    requester_email     TEXT,
    requester_company   TEXT,
    product_name        TEXT,
    message             TEXT,
    status              TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'fulfilled', 'declined')),
    fulfilled_share_id  BIGINT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pcf_requests_org_id ON pcf_requests (org_id);
CREATE INDEX IF NOT EXISTS idx_pcf_requests_status ON pcf_requests (status);

ALTER TABLE pcf_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY pcf_requests_select_member ON pcf_requests
    FOR SELECT TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );

CREATE POLICY pcf_requests_update_member ON pcf_requests
    FOR UPDATE TO authenticated
    USING (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    )
    WITH CHECK (
        org_id IN (SELECT org_id FROM org_members WHERE user_id = auth.uid())
    );
