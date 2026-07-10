-- Scope 3 · Epic A · per-category rollup for an inventory version. Cat 1 may be
-- sourced from the product-PCF rollup (method='product_rollup') instead of
-- spend, recorded in `method` so provenance is explicit and there is no
-- double-count.

CREATE TABLE IF NOT EXISTS s3_inventory_category_results (
    result_id        BIGSERIAL PRIMARY KEY,
    inventory_id     BIGINT NOT NULL REFERENCES s3_inventory_versions (inventory_id) ON DELETE CASCADE,
    org_id           UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    scope3_category  SMALLINT NOT NULL CHECK (scope3_category BETWEEN 1 AND 15),
    method           TEXT NOT NULL DEFAULT 'spend'
                     CHECK (method IN ('spend', 'product_rollup', 'activity')),
    total_kg_co2e    DOUBLE PRECISION NOT NULL DEFAULT 0,
    line_count       INTEGER NOT NULL DEFAULT 0,
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (inventory_id, scope3_category)
);

CREATE INDEX IF NOT EXISTS idx_s3_inventory_category_results_org ON s3_inventory_category_results (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_inventory_category_results_inventory ON s3_inventory_category_results (inventory_id);

ALTER TABLE s3_inventory_category_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_inventory_category_results_select ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_select ON s3_inventory_category_results
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_category_results_insert ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_insert ON s3_inventory_category_results
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_category_results_update ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_update ON s3_inventory_category_results
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_category_results_delete ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_delete ON s3_inventory_category_results
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));
