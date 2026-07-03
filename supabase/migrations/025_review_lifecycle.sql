-- Maker-checker review lifecycle (Wave 1 Workstream D)

ALTER TABLE products DROP CONSTRAINT IF EXISTS products_status_check;
ALTER TABLE products ADD CONSTRAINT products_status_check
    CHECK (status IN ('approved', 'flagged', 'under_review', 'published'));

ALTER TABLE products
    ADD COLUMN IF NOT EXISTS submitted_for_review_by UUID,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reviewed_by UUID,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS review_comment TEXT;
