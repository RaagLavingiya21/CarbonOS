-- Scope 3 · Epic D · per-category coverage for a target (V2.0 needs every
-- category >=5% of Scope 3 covered).

CREATE TABLE IF NOT EXISTS s3_target_categories (
    id                 BIGSERIAL PRIMARY KEY,
    target_id          BIGINT NOT NULL REFERENCES s3_targets (target_id) ON DELETE CASCADE,
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    category_num       SMALLINT NOT NULL CHECK (category_num BETWEEN 1 AND 15),
    pct_of_scope3      DOUBLE PRECISION,
    requires_coverage  BOOLEAN NOT NULL DEFAULT false,
    is_covered         BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (target_id, category_num)
);

CREATE INDEX IF NOT EXISTS idx_s3_target_categories_org ON s3_target_categories (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_target_categories_target ON s3_target_categories (target_id);

ALTER TABLE s3_target_categories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_target_categories_select ON s3_target_categories;
CREATE POLICY s3_target_categories_select ON s3_target_categories
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_categories_insert ON s3_target_categories;
CREATE POLICY s3_target_categories_insert ON s3_target_categories
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_categories_update ON s3_target_categories;
CREATE POLICY s3_target_categories_update ON s3_target_categories
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_categories_delete ON s3_target_categories;
CREATE POLICY s3_target_categories_delete ON s3_target_categories
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
