-- Scope 3 · Epic E · add the emission-factor library version to the per-category
-- rollup so progress decomposition can attribute EF-version changes (not just
-- method switches) as method-driven change rather than a real reduction.
--
-- Patch migration (ALTER only — no new table/RLS; s3_inventory_category_results
-- already carries org_id + is_org_member RLS from migration 303). Band 320+
-- (Scope 3 owns 300-399). Re-runnable via ADD COLUMN IF NOT EXISTS.

ALTER TABLE s3_inventory_category_results
    ADD COLUMN IF NOT EXISTS ef_version TEXT NOT NULL DEFAULT 'CEDA-2025';
