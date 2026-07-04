-- Scope 1 module (isolated): global reference data — gas species, GWP versions
-- and values, the EPA emission-factor library, and reporting-regime config.
-- These are NOT org-scoped. They are shared reference data: readable by every
-- authenticated user (like `suppliers`), writable only via the service role
-- (seed script). GWP lives in its own table and is applied at reporting time,
-- never baked into stored records. See research/2.1 and 2.2.

CREATE TABLE IF NOT EXISTS s1_gas_species (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cas_number         TEXT UNIQUE,
    common_name        TEXT NOT NULL UNIQUE,
    gas_family         TEXT NOT NULL,                          -- CO2|CH4|N2O|HFC|PFC|SF6|NF3|blend
    is_blend           BOOLEAN NOT NULL DEFAULT false,
    molecular_weight   NUMERIC(8,3),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Blends (e.g. R-410A) decompose into component species that sum to 1.0.
CREATE TABLE IF NOT EXISTS s1_gas_blend_component (
    blend_id       UUID NOT NULL REFERENCES s1_gas_species (id) ON DELETE CASCADE,      -- is_blend = true
    component_id   UUID NOT NULL REFERENCES s1_gas_species (id) ON DELETE CASCADE,      -- is_blend = false
    mass_fraction  NUMERIC(7,6) NOT NULL,                       -- components sum to 1.0
    PRIMARY KEY (blend_id, component_id)
);

CREATE TABLE IF NOT EXISTS s1_gwp_version (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ar_version        TEXT NOT NULL UNIQUE,                    -- AR4|AR5|AR6
    publication_year  INT NOT NULL,
    ipcc_reference    TEXT,
    is_current        BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS s1_gwp_value (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gwp_version_id    UUID NOT NULL REFERENCES s1_gwp_version (id) ON DELETE CASCADE,
    gas_species_id    UUID NOT NULL REFERENCES s1_gas_species (id) ON DELETE CASCADE,
    carbon_source     TEXT NOT NULL DEFAULT 'all',             -- all | fossil | biogenic (AR6 CH4 only)
    gwp_100           NUMERIC(10,2) NOT NULL,
    gwp_20            NUMERIC(10,2),
    UNIQUE (gwp_version_id, gas_species_id, carbon_source)
);

-- EPA-anchored emission-factor library. One row per (fuel/activity, gas). Stores
-- gas EFs only, never a CO2e factor. Superseded factors are kept (valid_to set),
-- never deleted, so base-year recalcs can reference the historical factor.
CREATE TABLE IF NOT EXISTS s1_ef_record (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fuel_or_activity   TEXT NOT NULL,                          -- natural_gas_pipeline|diesel_no2|motor_gasoline|...
    source_category    TEXT NOT NULL,                          -- stationary_combustion|mobile_onroad|mobile_nonroad
    gas                TEXT NOT NULL,                          -- CO2|CH4|N2O (avoid storing CO2e)
    value              NUMERIC(18,9) NOT NULL,
    unit               TEXT NOT NULL,                          -- kg/mmBtu|kg/gal|g/mile|kg/scf
    hhv                NUMERIC(18,9),                          -- default higher heating value (if energy basis)
    hhv_unit           TEXT,                                   -- mmBtu/scf|mmBtu/gal|mmBtu/ton
    source             TEXT NOT NULL,                          -- 'EPA EF Hub 2025 Table 1' / '40 CFR Part 98 C-1'
    source_version     TEXT NOT NULL,                          -- '2025-01-15'
    source_url         TEXT,
    region             TEXT NOT NULL DEFAULT 'US',             -- US|GB|GLOBAL
    tier               SMALLINT,                               -- 1|2|3
    biogenic           BOOLEAN NOT NULL DEFAULT false,
    model_year         INT,                                    -- mobile on-road CH4/N2O distance EFs
    valid_from         DATE NOT NULL,
    valid_to           DATE,                                   -- NULL = active; never delete superseded
    notes              TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_ef_record_active
    ON s1_ef_record (fuel_or_activity, source_category, gas, region)
    WHERE valid_to IS NULL;

CREATE TABLE IF NOT EXISTS s1_reporting_regime_config (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regime_name       TEXT UNIQUE NOT NULL,                    -- ESRS_E1|EPA_GHGRP|GHG_Protocol|CA_SB_253|CDP
    gwp_version_id    UUID REFERENCES s1_gwp_version (id),
    gwp_hybrid_rule   TEXT,                                    -- 'prefer_ar5_fallback_ar6' for EPA
    effective_from    DATE,
    effective_to      DATE
);
