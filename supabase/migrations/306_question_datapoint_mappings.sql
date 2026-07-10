-- Scope 3 · Epic B · question -> inventory-datapoint mapping + drafted answer.
-- mapped_value is ALWAYS a looked-up inventory datapoint (never generated);
-- unmappable questions carry flag_status='needs_human' with a null value.

CREATE TABLE IF NOT EXISTS s3_question_datapoint_mappings (
    mapping_id        BIGSERIAL PRIMARY KEY,
    question_id       BIGINT NOT NULL REFERENCES s3_questionnaire_questions (question_id) ON DELETE CASCADE,
    org_id            UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    datapoint_ref     TEXT,
    mapped_value      DOUBLE PRECISION,
    answer_text       TEXT,
    confidence_score  DOUBLE PRECISION,
    method            TEXT NOT NULL DEFAULT 'unmapped'
                      CHECK (method IN ('inventory', 'library', 'unmapped')),
    citation          TEXT,
    flag_status       TEXT NOT NULL DEFAULT 'needs_human',
    is_override       BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_qd_mappings_org ON s3_question_datapoint_mappings (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_qd_mappings_question ON s3_question_datapoint_mappings (question_id);

ALTER TABLE s3_question_datapoint_mappings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_qd_mappings_select ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_select ON s3_question_datapoint_mappings
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_qd_mappings_insert ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_insert ON s3_question_datapoint_mappings
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_qd_mappings_update ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_update ON s3_question_datapoint_mappings
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_qd_mappings_delete ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_delete ON s3_question_datapoint_mappings
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
