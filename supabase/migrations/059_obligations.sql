-- Scope 3 · Epic C · evaluated obligations per org (snapshot of an engine run).
-- The ruleset itself is versioned DATA in the s3_obligations package, not a
-- table; this stores the OUTPUT of evaluating a profile against it.

CREATE TABLE IF NOT EXISTS s3_obligations (
    obligation_id     BIGSERIAL PRIMARY KEY,
    org_id            UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id           UUID REFERENCES auth.users (id),   -- created_by metadata only
    rule_id           TEXT NOT NULL,
    framework         TEXT NOT NULL,
    applies           TEXT NOT NULL CHECK (applies IN ('yes', 'uncertain', 'no')),
    reason            TEXT,
    threshold_detail  TEXT,
    confidence        TEXT,
    status            TEXT,
    due               JSONB NOT NULL DEFAULT '[]'::jsonb,
    assurance         TEXT,
    citation          TEXT,
    priority          INTEGER NOT NULL DEFAULT 0,
    ruleset_version   TEXT NOT NULL,
    evaluated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_obligations_org ON s3_obligations (org_id);

ALTER TABLE s3_obligations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_obligations_select ON s3_obligations;
CREATE POLICY s3_obligations_select ON s3_obligations
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_obligations_insert ON s3_obligations;
CREATE POLICY s3_obligations_insert ON s3_obligations
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_obligations_update ON s3_obligations;
CREATE POLICY s3_obligations_update ON s3_obligations
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_obligations_delete ON s3_obligations;
CREATE POLICY s3_obligations_delete ON s3_obligations
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
