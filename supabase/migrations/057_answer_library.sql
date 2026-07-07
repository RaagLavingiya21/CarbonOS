-- Scope 3 · Epic B · reusable prior answers (the compounding moat). On submit,
-- answered questions are written here keyed by framework_field_key /
-- question_signature so the next questionnaire can reuse them.

CREATE TABLE IF NOT EXISTS s3_answer_library (
    answer_id            BIGSERIAL PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id              UUID REFERENCES auth.users (id),   -- created_by metadata only
    framework_field_key  TEXT,
    question_signature   TEXT,
    answer_text          TEXT NOT NULL,
    source_request_id    BIGINT REFERENCES s3_questionnaire_requests (request_id) ON DELETE SET NULL,
    last_used_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_answer_library_org ON s3_answer_library (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_answer_library_key ON s3_answer_library (org_id, framework_field_key);

ALTER TABLE s3_answer_library ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_answer_library_select ON s3_answer_library;
CREATE POLICY s3_answer_library_select ON s3_answer_library
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_answer_library_insert ON s3_answer_library;
CREATE POLICY s3_answer_library_insert ON s3_answer_library
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_answer_library_update ON s3_answer_library;
CREATE POLICY s3_answer_library_update ON s3_answer_library
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_answer_library_delete ON s3_answer_library;
CREATE POLICY s3_answer_library_delete ON s3_answer_library
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
