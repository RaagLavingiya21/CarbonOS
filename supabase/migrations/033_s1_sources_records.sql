-- Scope 1 module (isolated): emission sources and the per-gas emission records.
-- THE atomic record is gas masses in kg per species (immutable). There is NO
-- CO2e column anywhere here — CO2e is derived at reporting time by applying a
-- GWP version. `scope` enum keeps the model scope-agnostic (S2/S3 attach later
-- via extension tables with zero changes). See research/2.1 section 5, 2.2 C2.

CREATE TABLE IF NOT EXISTS s1_emission_source (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    entity_id             UUID NOT NULL REFERENCES s1_legal_entity (id) ON DELETE CASCADE,
    facility_id           UUID REFERENCES s1_facility (id) ON DELETE SET NULL,
    scope                 TEXT NOT NULL DEFAULT 'scope_1',     -- scope_1|scope_2|scope_3
    source_name           TEXT NOT NULL,
    source_category       TEXT NOT NULL,                       -- stationary_combustion|mobile_combustion|process_emissions|fugitive_emissions
    source_subcategory    TEXT,
    primary_fuel          TEXT,                                -- natural_gas|diesel_no2|propane|motor_gasoline|...
    primary_fuel_gas_id   UUID REFERENCES s1_gas_species (id),
    ghgrp_subpart         TEXT,                                -- C|W|H|I|F|Q ... NULL if not GHGRP
    -- Mobile-combustion specifics (model year drives CH4/N2O EF selection).
    vehicle_class         TEXT,
    vehicle_model_year    INT,
    location_lat          NUMERIC(9,6),
    location_lon          NUMERIC(9,6),
    is_excluded           BOOLEAN NOT NULL DEFAULT false,      -- GHG Protocol completeness: exclude + document
    exclusion_rationale   TEXT,
    active_from           DATE,
    active_to             DATE,
    created_by            UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_source_org_id ON s1_emission_source (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_source_entity ON s1_emission_source (entity_id);
CREATE INDEX IF NOT EXISTS idx_s1_source_facility ON s1_emission_source (facility_id);

CREATE TABLE IF NOT EXISTS s1_emission_record (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id          UUID NOT NULL REFERENCES s1_inventory (id) ON DELETE CASCADE,
    emission_source_id    UUID NOT NULL REFERENCES s1_emission_source (id) ON DELETE CASCADE,
    scope                 TEXT NOT NULL DEFAULT 'scope_1',
    period_start          DATE NOT NULL,
    period_end            DATE NOT NULL,
    -- Activity data
    activity_data_value   NUMERIC(18,6) NOT NULL,
    activity_data_unit    TEXT NOT NULL,                       -- GJ|therms|CCF|MCF|mmBtu|gal|L|km|mi|scf|ton
    fuel_qty_native       NUMERIC(18,6),                       -- as-entered, before normalization
    fuel_billing_unit     TEXT,                                -- therms|Ccf|mmBtu|gallons|tons|scf
    heat_input_mmbtu      NUMERIC(18,6),                       -- auditable intermediate
    activity_data_source  TEXT,                                -- utility_invoice|fuel_card|manual|CEMS_meter
    calculation_method    TEXT,                                -- EF_Tier1|EF_Tier2|carbon_content_Tier3|distance_based|CEMS
    calorific_value_basis TEXT,                                -- HHV|LHV; NULL non-combustion
    hhv_source            TEXT,
    -- Emission-factor provenance (the specific EF rows applied, snapshotted)
    ef_id_co2             UUID REFERENCES s1_ef_record (id),
    ef_id_ch4             UUID REFERENCES s1_ef_record (id),
    ef_id_n2o             UUID REFERENCES s1_ef_record (id),
    ef_source             TEXT NOT NULL,                       -- 'EPA EF Hub Table 1 Jan-2025'
    ef_tier               TEXT NOT NULL,                       -- T1|T2|T3
    ef_selection_rank     INT,                                 -- 1 measured .. 5 IPCC-default
    ef_publication_year   INT,
    -- GAS MASSES (kg) — immutable physical record; NO CO2e column here.
    kg_co2_fossil         NUMERIC(18,6),
    kg_co2_biogenic       NUMERIC(18,6),                       -- separate disclosure; excluded from S1 total
    kg_ch4                NUMERIC(18,6),
    kg_n2o                NUMERIC(18,6),
    kg_sf6                NUMERIC(18,6),
    kg_nf3                NUMERIC(18,6),
    hfc_pfc_species_id    UUID REFERENCES s1_gas_species (id), -- single-species convenience
    kg_hfc_pfc_primary    NUMERIC(18,6),                       -- blends -> s1_emission_record_gas_detail
    biogenic_fossil_tag   TEXT NOT NULL,                       -- fossil|biogenic|mixed|not_applicable
    data_quality_tier     SMALLINT NOT NULL,                   -- 1..5 (T1 metered .. T5 estimated)
    uncertainty_pct_low   NUMERIC(6,2),
    uncertainty_pct_high  NUMERIC(6,2),
    uncertainty_basis     TEXT,                                -- quantitative|qualitative
    evidence_document_id  UUID,                                -- FK added in migration 035
    locked                BOOLEAN NOT NULL DEFAULT false,
    lock_reason           TEXT,
    corrects_record_id    UUID REFERENCES s1_emission_record (id),  -- non-NULL = correction row
    created_by            UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT s1_emission_record_tag_chk
        CHECK (biogenic_fossil_tag IN ('fossil', 'biogenic', 'mixed', 'not_applicable')),
    CONSTRAINT s1_emission_record_tier_chk
        CHECK (data_quality_tier BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS idx_s1_record_org_id ON s1_emission_record (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_record_inventory ON s1_emission_record (inventory_id);
CREATE INDEX IF NOT EXISTS idx_s1_record_source ON s1_emission_record (emission_source_id);

-- Species-level detail for HFC/PFC and blends (populated in V1; table exists now).
CREATE TABLE IF NOT EXISTS s1_emission_record_gas_detail (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    emission_record_id    UUID NOT NULL REFERENCES s1_emission_record (id) ON DELETE CASCADE,
    gas_species_id        UUID NOT NULL REFERENCES s1_gas_species (id),
    kg_emitted            NUMERIC(18,6) NOT NULL,
    parent_blend_id       UUID REFERENCES s1_gas_species (id),
    mass_fraction_applied NUMERIC(7,6),
    UNIQUE (emission_record_id, gas_species_id)
);

CREATE INDEX IF NOT EXISTS idx_s1_gas_detail_org_id ON s1_emission_record_gas_detail (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_gas_detail_record ON s1_emission_record_gas_detail (emission_record_id);
