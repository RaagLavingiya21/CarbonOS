-- Scope 1 module (isolated): inventory (reporting-year dataset), consolidation
-- boundary, and the append-only boundary-decision log.
-- Axioms (research/2.2): consolidation_approach is inventory-level and immutable;
-- one approach per (entity, year); CO2e is never stored (derived at reporting time).

CREATE TABLE IF NOT EXISTS s1_inventory (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                      UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    reporting_entity_id         UUID NOT NULL REFERENCES s1_legal_entity (id) ON DELETE CASCADE,
    reporting_year              INT NOT NULL,
    -- Fiscal-year support: SB 253 reports a fiscal year, not just a calendar year.
    period_start                DATE NOT NULL,
    period_end                  DATE NOT NULL,
    consolidation_approach      TEXT NOT NULL,                 -- equity_share|financial_control|operational_control
    base_year                   INT NOT NULL,
    base_year_total_tco2e       NUMERIC(18,4),
    base_year_gwp_version       TEXT,                          -- AR4|AR5|AR6
    significance_threshold_pct  NUMERIC(6,2),                  -- declared with the base year (recalc engine is V1)
    status                      TEXT NOT NULL DEFAULT 'draft', -- draft|final|verified|restated
    assurance_level             TEXT,                          -- none|limited|reasonable
    assurance_standard          TEXT,                          -- ISAE_3410|ISSA_5000|ISO_14064-3
    locked                      BOOLEAN NOT NULL DEFAULT false,
    locked_at                   TIMESTAMPTZ,
    locked_by                   UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_by                  UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT s1_inventory_approach_chk
        CHECK (consolidation_approach IN ('equity_share', 'financial_control', 'operational_control')),
    -- One approach per (entity, year) — consistency enforced at schema level.
    UNIQUE (reporting_entity_id, reporting_year)
);

CREATE INDEX IF NOT EXISTS idx_s1_inventory_org_id ON s1_inventory (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_inventory_entity ON s1_inventory (reporting_entity_id);

-- Per-entity boundary within an inventory. consolidation_multiplier is LOAD-BEARING:
-- computed from approach + control flags, stored for audit. [0.0-1.0].
CREATE TABLE IF NOT EXISTS s1_inventory_entity_boundary (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                   UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id             UUID NOT NULL REFERENCES s1_inventory (id) ON DELETE CASCADE,
    entity_id                UUID NOT NULL REFERENCES s1_legal_entity (id) ON DELETE CASCADE,
    in_scope                 BOOLEAN NOT NULL,
    exclusion_reason         TEXT,
    applied_equity_pct       NUMERIC(7,4),
    consolidation_multiplier NUMERIC(7,6) NOT NULL,            -- [0.0-1.0]
    consolidation_rationale  TEXT NOT NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (inventory_id, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_s1_boundary_org_id ON s1_inventory_entity_boundary (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_boundary_inventory ON s1_inventory_entity_boundary (inventory_id);

-- Append-only boundary-decision log (leased buildings, JVs, divestitures, leased
-- cars): what / who / why / when. No UPDATE/DELETE (enforced in RLS migration 036).
CREATE TABLE IF NOT EXISTS s1_boundary_decision_log (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id   UUID REFERENCES s1_inventory (id) ON DELETE CASCADE,
    entity_id      UUID REFERENCES s1_legal_entity (id) ON DELETE SET NULL,
    decision_type  TEXT NOT NULL,                              -- leased_building|jv|divestiture|leased_vehicle|exclusion|approach_change|other
    decision       TEXT NOT NULL,                              -- what was decided
    rationale      TEXT NOT NULL,                              -- why
    decided_by     UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    decided_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_boundary_log_org_id ON s1_boundary_decision_log (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_boundary_log_inventory ON s1_boundary_decision_log (inventory_id);
