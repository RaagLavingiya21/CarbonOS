-- Annual production/sales volume per product lineage and reporting year (Wave 3 roll-up).
-- Volume is business metadata — not stored on immutable published footprints.

CREATE TABLE IF NOT EXISTS product_volumes (
    volume_id           BIGSERIAL PRIMARY KEY,
    product_lineage_id  UUID NOT NULL,
    user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    year                INTEGER NOT NULL,
    annual_volume       DOUBLE PRECISION NOT NULL CHECK (annual_volume >= 0),
    unit                TEXT NOT NULL DEFAULT 'units',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (product_lineage_id, year)
);

CREATE INDEX IF NOT EXISTS idx_product_volumes_lineage ON product_volumes (product_lineage_id);
CREATE INDEX IF NOT EXISTS idx_product_volumes_user ON product_volumes (user_id);

ALTER TABLE product_volumes ENABLE ROW LEVEL SECURITY;

-- Read: owner or org teammate (mirrors products visibility).
CREATE POLICY product_volumes_select_own ON product_volumes
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY product_volumes_select_org ON product_volumes
    FOR SELECT TO authenticated
    USING (public.shares_org_with(user_id));

-- Write: any org member who can see a product in the lineage.
CREATE POLICY product_volumes_insert_org ON product_volumes
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM products p
            WHERE p.product_lineage_id = product_volumes.product_lineage_id
              AND (p.user_id = auth.uid() OR public.shares_org_with(p.user_id))
        )
    );

CREATE POLICY product_volumes_update_org ON product_volumes
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM products p
            WHERE p.product_lineage_id = product_volumes.product_lineage_id
              AND (p.user_id = auth.uid() OR public.shares_org_with(p.user_id))
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM products p
            WHERE p.product_lineage_id = product_volumes.product_lineage_id
              AND (p.user_id = auth.uid() OR public.shares_org_with(p.user_id))
        )
    );

CREATE POLICY product_volumes_delete_org ON product_volumes
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM products p
            WHERE p.product_lineage_id = product_volumes.product_lineage_id
              AND (p.user_id = auth.uid() OR public.shares_org_with(p.user_id))
        )
    );
