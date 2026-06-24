-- Product footprint analyses (user-owned)

CREATE TABLE IF NOT EXISTS products (
    product_id      BIGSERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    product_name    TEXT NOT NULL,
    analysis_date   DATE NOT NULL,
    total_kg_co2e   DOUBLE PRECISION NOT NULL,
    matched_items   INTEGER NOT NULL,
    flagged_items   INTEGER NOT NULL,
    status          TEXT NOT NULL DEFAULT 'approved',
    flagged_comment TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_user_id ON products (user_id);
CREATE INDEX IF NOT EXISTS idx_products_analysis_date ON products (analysis_date DESC);
CREATE INDEX IF NOT EXISTS idx_products_user_name ON products (user_id, product_name);

CREATE TABLE IF NOT EXISTS line_items (
    item_id         BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    component       TEXT,
    material        TEXT,
    spend_usd       DOUBLE PRECISION,
    matched_sector  TEXT,
    emission_factor DOUBLE PRECISION,
    ef_source       TEXT,
    kg_co2e         DOUBLE PRECISION,
    share_pct       DOUBLE PRECISION,
    flag_status     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_line_items_product_id ON line_items (product_id);
CREATE INDEX IF NOT EXISTS idx_line_items_user_id ON line_items (user_id);
