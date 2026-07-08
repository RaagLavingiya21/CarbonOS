-- Scope 3 · Epic E · progress snapshots (like-for-like real reduction vs a
-- target trajectory). Band 310+. org_id RLS via public.is_org_member(org_id).

CREATE TABLE IF NOT EXISTS s3_target_progress (
    progress_id           BIGSERIAL PRIMARY KEY,
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id               UUID REFERENCES auth.users (id),   -- created_by metadata only
    target_id             BIGINT REFERENCES s3_targets (target_id) ON DELETE SET NULL,
    base_inventory_id     BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    current_inventory_id  BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    current_year          INTEGER,
    actual_total_kg       DOUBLE PRECISION,
    real_total_kg         DOUBLE PRECISION,
    method_delta_kg       DOUBLE PRECISION,
    on_track              BOOLEAN,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_target_progress_org ON s3_target_progress (org_id);

ALTER TABLE s3_target_progress ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_target_progress_select ON s3_target_progress;
CREATE POLICY s3_target_progress_select ON s3_target_progress
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_progress_insert ON s3_target_progress;
CREATE POLICY s3_target_progress_insert ON s3_target_progress
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_progress_update ON s3_target_progress;
CREATE POLICY s3_target_progress_update ON s3_target_progress
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_progress_delete ON s3_target_progress;
CREATE POLICY s3_target_progress_delete ON s3_target_progress
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
