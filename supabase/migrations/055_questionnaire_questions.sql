-- Scope 3 · Epic B · parsed questions for a questionnaire request.

CREATE TABLE IF NOT EXISTS s3_questionnaire_questions (
    question_id          BIGSERIAL PRIMARY KEY,
    request_id           BIGINT NOT NULL REFERENCES s3_questionnaire_requests (request_id) ON DELETE CASCADE,
    org_id               UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    question_index       INTEGER NOT NULL DEFAULT 0,
    section              TEXT,
    question_text        TEXT NOT NULL,
    question_type        TEXT NOT NULL DEFAULT 'narrative'
                         CHECK (question_type IN ('numeric', 'boolean', 'select', 'narrative')),
    framework_field_key  TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_questionnaire_questions_org ON s3_questionnaire_questions (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_questionnaire_questions_request ON s3_questionnaire_questions (request_id);

ALTER TABLE s3_questionnaire_questions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_questionnaire_questions_select ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_select ON s3_questionnaire_questions
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_questions_insert ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_insert ON s3_questionnaire_questions
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_questions_update ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_update ON s3_questionnaire_questions
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_questions_delete ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_delete ON s3_questionnaire_questions
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
