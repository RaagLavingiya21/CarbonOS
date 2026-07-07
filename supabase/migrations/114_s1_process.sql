-- Scope 1 — process emissions (direct emissions from chemical / physical
-- transformation of materials; not combustion, not fugitive).
--
-- Stores the emitted gas MASS (kg of CO2 / CH4 / N2O), computed server-side as
-- activity x process emission factor — never CO2e. tCO2e is derived at reporting
-- time via the gas GWP for the chosen AR version (same principle as combustion).
-- The process type + factor inputs are kept for View Source / audit.
--
-- Band: Scope 1 = 110–199.

CREATE TABLE IF NOT EXISTS s1_process_record (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id               UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id         UUID NOT NULL REFERENCES s1_inventory (id) ON DELETE CASCADE,
    facility_id          UUID REFERENCES s1_facility (id) ON DELETE SET NULL,
    process_type         TEXT NOT NULL,                       -- cement_clinker|lime|nitric_acid|...|custom
    gas_species          TEXT NOT NULL,                       -- Carbon dioxide|Methane|Nitrous oxide
    activity_quantity    NUMERIC(20,4) NOT NULL,
    activity_unit        TEXT,
    ef_value             NUMERIC(20,6) NOT NULL,              -- kg gas / activity_unit
    ef_unit              TEXT,
    emission_kg          NUMERIC(20,4) NOT NULL,              -- derived mass (server-computed)
    ef_source            TEXT,
    description          TEXT,
    period_start         DATE,
    period_end           DATE,
    data_quality_tier    SMALLINT DEFAULT 4,
    evidence_document_id UUID REFERENCES s1_evidence_document (id) ON DELETE SET NULL,
    created_by           UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT s1_process_gas_chk CHECK (gas_species IN ('Carbon dioxide', 'Methane', 'Nitrous oxide'))
);

CREATE INDEX IF NOT EXISTS idx_s1_process_inventory
    ON s1_process_record (inventory_id);

-- RLS: org-scoped tenancy via is_org_member; app-layer refines write access.
ALTER TABLE s1_process_record ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_process_select_org ON s1_process_record;
CREATE POLICY s1_process_select_org ON s1_process_record
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_process_insert_org ON s1_process_record;
CREATE POLICY s1_process_insert_org ON s1_process_record
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_process_update_org ON s1_process_record;
CREATE POLICY s1_process_update_org ON s1_process_record
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_process_delete_org ON s1_process_record;
CREATE POLICY s1_process_delete_org ON s1_process_record
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));
