-- Scope 1 — per-org emission-factor overrides (MVP gap #5, PRD C1).
--
-- The shared `s1_ef_record` table is global EPA reference data (read-only to
-- tenants; refreshed by the platform). This table lets an org's Scope-1 ADMIN
-- layer their own factor(s) on top of it — e.g. early-adopt a new EPA year, or
-- record a measured / supplier-specific factor — WITHOUT ever mutating the
-- shared reference set. The loader replaces the global factor for a matching
-- (fuel, category, gas, region, model_year) key with the org's active override.
--
-- Versioned like s1_ef_record: superseding a factor sets `valid_to` on the old
-- row and inserts a new active row (valid_to IS NULL), so historical factors
-- remain available for base-year recalcs. Never hard-delete.
--
-- Band: Scope 1 = 110–199 (granted 2026-07-07; original 030–039 is full).

CREATE TABLE IF NOT EXISTS s1_ef_override (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    fuel_or_activity   TEXT NOT NULL,
    source_category    TEXT NOT NULL,
    gas                TEXT NOT NULL,                          -- CO2|CH4|N2O (never CO2e)
    value              NUMERIC(18,9) NOT NULL,
    unit               TEXT NOT NULL,                          -- kg/mmBtu|kg/gal|g/mile|kg/scf
    hhv                NUMERIC(18,9),
    hhv_unit           TEXT,
    source             TEXT NOT NULL,                          -- provenance the org cites
    source_version     TEXT NOT NULL,                          -- e.g. 'EPA EF Hub 2026-01' / 'Supplier attestation 2025'
    region             TEXT NOT NULL DEFAULT 'US',
    tier               SMALLINT,
    biogenic           BOOLEAN NOT NULL DEFAULT false,
    model_year         INT,                                    -- mobile on-road distance EFs
    basis              TEXT NOT NULL DEFAULT 'custom',         -- measured|supplier|custom (sets selection rank)
    valid_from         DATE NOT NULL DEFAULT now(),
    valid_to           DATE,                                   -- NULL = active; never delete superseded
    notes              TEXT,
    created_by         UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT s1_ef_override_basis_chk CHECK (basis IN ('measured', 'supplier', 'custom')),
    CONSTRAINT s1_ef_override_gas_chk   CHECK (gas IN ('CO2', 'CH4', 'N2O'))
);

-- One active override per (org, fuel, category, gas, region, model_year).
CREATE UNIQUE INDEX IF NOT EXISTS idx_s1_ef_override_active
    ON s1_ef_override (org_id, fuel_or_activity, source_category, gas, region, COALESCE(model_year, -1))
    WHERE valid_to IS NULL;

-- RLS: org-scoped tenancy via is_org_member (the mandated standard). Admin-only
-- WRITES are enforced in the app layer (require_admin), matching s1_member_role.
ALTER TABLE s1_ef_override ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_ef_override_select_org ON s1_ef_override;
CREATE POLICY s1_ef_override_select_org ON s1_ef_override
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_ef_override_insert_org ON s1_ef_override;
CREATE POLICY s1_ef_override_insert_org ON s1_ef_override
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_ef_override_update_org ON s1_ef_override;
CREATE POLICY s1_ef_override_update_org ON s1_ef_override
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_ef_override_delete_org ON s1_ef_override;
CREATE POLICY s1_ef_override_delete_org ON s1_ef_override
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));
