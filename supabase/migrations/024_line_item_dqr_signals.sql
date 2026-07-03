-- DQR signals and aggregate scores (Wave 1 Workstream A)

ALTER TABLE line_items
    ADD COLUMN IF NOT EXISTS ef_confidence DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS country_of_origin TEXT,
    ADD COLUMN IF NOT EXISTS technological_dqr SMALLINT,
    ADD COLUMN IF NOT EXISTS geographical_dqr SMALLINT,
    ADD COLUMN IF NOT EXISTS temporal_dqr SMALLINT;

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS technological_dqr SMALLINT,
    ADD COLUMN IF NOT EXISTS geographical_dqr SMALLINT,
    ADD COLUMN IF NOT EXISTS temporal_dqr SMALLINT,
    ADD COLUMN IF NOT EXISTS dqr_computed_at TIMESTAMPTZ;
