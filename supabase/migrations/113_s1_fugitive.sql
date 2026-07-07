-- Scope 1 — fugitive emissions (refrigerant leakage from AC / refrigeration).
--
-- Stores the estimated leaked *mass* (kg of a refrigerant) plus the method and
-- its inputs — never CO2e. tCO2e is derived at reporting time by applying the
-- refrigerant's GWP for the chosen AR version (same principle as combustion gas
-- masses). Superseded/edited records are deleted, not versioned (intake data).
--
-- Band: Scope 1 = 110–199.

CREATE TABLE IF NOT EXISTS s1_fugitive_record (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                   UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id             UUID NOT NULL REFERENCES s1_inventory (id) ON DELETE CASCADE,
    facility_id              UUID REFERENCES s1_facility (id) ON DELETE SET NULL,
    refrigerant              TEXT NOT NULL,                    -- R-410A|R-134a|...
    method                   TEXT NOT NULL,                    -- screening|material_balance
    leaked_kg                NUMERIC(18,4) NOT NULL,           -- derived mass (server-computed)
    -- Method inputs (kept for View Source / audit):
    charge_kg                NUMERIC(18,4),
    leak_rate_pct            NUMERIC(8,4),
    purchases_kg             NUMERIC(18,4),
    beginning_inventory_kg   NUMERIC(18,4),
    ending_inventory_kg      NUMERIC(18,4),
    description              TEXT,
    period_start             DATE,
    period_end               DATE,
    data_quality_tier        SMALLINT DEFAULT 4,
    evidence_document_id     UUID REFERENCES s1_evidence_document (id) ON DELETE SET NULL,
    created_by               UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT s1_fugitive_method_chk CHECK (method IN ('screening', 'material_balance'))
);

CREATE INDEX IF NOT EXISTS idx_s1_fugitive_inventory
    ON s1_fugitive_record (inventory_id);

-- RLS: org-scoped tenancy via is_org_member; app-layer refines write access.
ALTER TABLE s1_fugitive_record ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_fugitive_select_org ON s1_fugitive_record;
CREATE POLICY s1_fugitive_select_org ON s1_fugitive_record
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_fugitive_insert_org ON s1_fugitive_record;
CREATE POLICY s1_fugitive_insert_org ON s1_fugitive_record
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_fugitive_update_org ON s1_fugitive_record;
CREATE POLICY s1_fugitive_update_org ON s1_fugitive_record
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_fugitive_delete_org ON s1_fugitive_record;
CREATE POLICY s1_fugitive_delete_org ON s1_fugitive_record
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));
