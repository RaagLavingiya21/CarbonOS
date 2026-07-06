-- Scope 1 module (isolated): organizational structure.
-- Models the customer's legal-entity tree + facilities for consolidation.
-- Tenant boundary = organizations.id (the platform org). Every s1_ table
-- carries org_id (denormalized) so RLS is uniform: USING (is_org_member(org_id)).
-- See research/2.2-data-model-spec.md section A2.

CREATE TABLE IF NOT EXISTS s1_legal_entity (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                   UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    parent_entity_id         UUID REFERENCES s1_legal_entity (id) ON DELETE SET NULL,  -- NULL for root
    name                     TEXT NOT NULL,
    jurisdiction             CHAR(2) NOT NULL,                 -- ISO 3166-1 alpha-2
    entity_type              TEXT NOT NULL,                    -- wholly_owned_subsidiary|majority_subsidiary|joint_venture|jointly_controlled_operation|associate|parent|leased_asset_entity
    equity_pct               NUMERIC(7,4),                     -- direct equity held by parent
    economic_interest_pct    NUMERIC(7,4),                     -- override if != equity_pct
    has_financial_control    BOOLEAN NOT NULL DEFAULT false,
    has_operational_control  BOOLEAN NOT NULL DEFAULT false,
    ghgrp_applicable         BOOLEAN NOT NULL DEFAULT false,
    ghgrp_facility_id        TEXT,                             -- EPA e-GGRT facility ID
    sb253_in_scope           BOOLEAN NOT NULL DEFAULT false,
    csrd_esrs_in_scope       BOOLEAN NOT NULL DEFAULT false,
    eu_ets_installation      BOOLEAN NOT NULL DEFAULT false,   -- ESRS E1 para.48
    effective_from           DATE NOT NULL,
    effective_to             DATE,                             -- NULL = active
    created_by               UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_legal_entity_org_id ON s1_legal_entity (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_legal_entity_parent ON s1_legal_entity (parent_entity_id);

-- Closure table for subtree queries + equity-chain math (product of equity_pct on path).
CREATE TABLE IF NOT EXISTS s1_entity_hierarchy_path (
    org_id            UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    ancestor_id       UUID NOT NULL REFERENCES s1_legal_entity (id) ON DELETE CASCADE,
    descendant_id     UUID NOT NULL REFERENCES s1_legal_entity (id) ON DELETE CASCADE,
    depth             INT NOT NULL,                            -- 0 = self
    equity_chain_pct  NUMERIC(7,4),                            -- product of equity_pct along the path
    PRIMARY KEY (ancestor_id, descendant_id)
);

CREATE INDEX IF NOT EXISTS idx_s1_entity_path_org_id ON s1_entity_hierarchy_path (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_entity_path_descendant ON s1_entity_hierarchy_path (descendant_id);

-- Facilities / sites under an entity (where combustion sources live).
CREATE TABLE IF NOT EXISTS s1_facility (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    entity_id      UUID NOT NULL REFERENCES s1_legal_entity (id) ON DELETE CASCADE,
    name           TEXT NOT NULL,
    address        TEXT,
    city           TEXT,
    state_region   TEXT,
    country        CHAR(2),                                    -- ISO 3166-1 alpha-2
    location_lat   NUMERIC(9,6),
    location_lon   NUMERIC(9,6),
    active_from    DATE,
    active_to      DATE,
    created_by     UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_facility_org_id ON s1_facility (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_facility_entity ON s1_facility (entity_id);
