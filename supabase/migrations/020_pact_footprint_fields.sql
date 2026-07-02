-- PACT v3-aligned footprint fields (see PCF_PLATFORM_DESIGN.md §7)

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS footprint_uuid          UUID NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS product_description     TEXT,
    ADD COLUMN IF NOT EXISTS declared_unit           TEXT NOT NULL DEFAULT 'piece',
    ADD COLUMN IF NOT EXISTS unitary_product_amount  DOUBLE PRECISION NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS system_boundary         TEXT NOT NULL DEFAULT 'cradle-to-gate',
    ADD COLUMN IF NOT EXISTS reporting_period_start  DATE,
    ADD COLUMN IF NOT EXISTS reporting_period_end    DATE,
    ADD COLUMN IF NOT EXISTS geography_country       TEXT,
    ADD COLUMN IF NOT EXISTS primary_data_share      DOUBLE PRECISION NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS spec_version            TEXT NOT NULL DEFAULT '3.0.0',
    ADD COLUMN IF NOT EXISTS version                 INTEGER NOT NULL DEFAULT 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_products_footprint_uuid ON products (footprint_uuid);

ALTER TABLE line_items
    ADD COLUMN IF NOT EXISTS data_source TEXT NOT NULL DEFAULT 'secondary'
        CHECK (data_source IN ('primary', 'secondary'));
