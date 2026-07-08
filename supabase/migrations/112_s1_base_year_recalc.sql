-- Scope 1 — base-year recalculation events (GHG Protocol Chapter 5).
--
-- Records the structural (and organic) change events that drive a base-year
-- restatement. Structural changes (acquisition/divestiture/out-insourcing/
-- methodology change/error correction) recalculate the base year; organic
-- changes are kept for transparency but never fold into the total. `applied`
-- marks an event already reflected in s1_inventory.base_year_total_tco2e (the
-- restatement itself is an append-only change-log entry, so history is kept).
--
-- No CO2e is stored as a factor — delta_tco2e is a signed base-year restatement
-- amount, consistent with how base-year totals are carried on s1_inventory.
--
-- Band: Scope 1 = 110–199.

CREATE TABLE IF NOT EXISTS s1_base_year_recalc_event (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id   UUID NOT NULL REFERENCES s1_inventory (id) ON DELETE CASCADE,
    trigger_type   TEXT NOT NULL,                     -- acquisition|divestiture|outsourcing|insourcing|methodology_change|error_correction|organic_growth|organic_decline
    description    TEXT,
    delta_tco2e    NUMERIC(18,4) NOT NULL,            -- signed: add(+) / remove(-) base-year emissions
    effective_date DATE,
    applied        BOOLEAN NOT NULL DEFAULT false,    -- folded into the stored base-year total
    applied_at     TIMESTAMPTZ,
    created_by     UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT s1_recalc_trigger_chk CHECK (trigger_type IN (
        'acquisition', 'divestiture', 'outsourcing', 'insourcing',
        'methodology_change', 'error_correction', 'organic_growth', 'organic_decline'
    ))
);

CREATE INDEX IF NOT EXISTS idx_s1_recalc_event_inventory
    ON s1_base_year_recalc_event (inventory_id);

-- RLS: org-scoped tenancy via is_org_member (mandated standard). Write access is
-- refined in the app layer (require_editor), matching the rest of Scope 1.
ALTER TABLE s1_base_year_recalc_event ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_recalc_event_select_org ON s1_base_year_recalc_event;
CREATE POLICY s1_recalc_event_select_org ON s1_base_year_recalc_event
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_recalc_event_insert_org ON s1_base_year_recalc_event;
CREATE POLICY s1_recalc_event_insert_org ON s1_base_year_recalc_event
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_recalc_event_update_org ON s1_base_year_recalc_event;
CREATE POLICY s1_recalc_event_update_org ON s1_base_year_recalc_event
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_recalc_event_delete_org ON s1_base_year_recalc_event;
CREATE POLICY s1_recalc_event_delete_org ON s1_base_year_recalc_event
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));
