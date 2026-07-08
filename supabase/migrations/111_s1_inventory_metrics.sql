-- Scope 1 — operational denominators for emissions-intensity reporting.
--
-- Adds nullable per-inventory operational metrics so the trends endpoint can
-- compute intensity (tCO2e per $M revenue / per output unit / per FTE) for
-- SB 253 / investor disclosure. No CO2e is stored — intensity is derived at
-- reporting time from these denominators and the rolled-up total.
--
-- Nullable + additive: existing inventories are unaffected; intensity simply
-- isn't shown until an editor fills the denominator. Existing s1_inventory RLS
-- (migration 036, is_org_member) already covers these columns.
--
-- Band: Scope 1 = 110–199.

ALTER TABLE s1_inventory
    ADD COLUMN IF NOT EXISTS annual_revenue    NUMERIC(20,2),   -- absolute, in revenue_currency
    ADD COLUMN IF NOT EXISTS revenue_currency  TEXT DEFAULT 'USD',
    ADD COLUMN IF NOT EXISTS output_quantity   NUMERIC(20,4),   -- physical output (e.g. units, tonnes, MWh)
    ADD COLUMN IF NOT EXISTS output_unit       TEXT,
    ADD COLUMN IF NOT EXISTS headcount         INT;
