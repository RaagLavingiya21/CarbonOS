-- Versioning lineage + publish lifecycle (see PCF_PLATFORM_DESIGN.md, Phase 2)

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS product_lineage_id UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS published_at        TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_products_lineage_id ON products (product_lineage_id);

ALTER TABLE products
    ADD CONSTRAINT products_status_check
    CHECK (status IN ('approved', 'flagged', 'published'));
