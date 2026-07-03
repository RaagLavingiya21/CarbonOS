-- Phase 3: record primary-data apply outcome on supplier engagements

ALTER TABLE engagements
    ADD COLUMN IF NOT EXISTS primary_kg_co2e      DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS applied_to_product_id BIGINT,
    ADD COLUMN IF NOT EXISTS pds_before           DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS pds_after            DOUBLE PRECISION;
