-- Scope 1 module (Phase 2): record which parser produced a review-queue row.
-- The queue now serves two extractors that share one review UI:
--   'claude'  -> our Vision-LLM OCR (Tier 3 general-purpose)
--   'bayou'   -> Bayou trained utility-bill parsers (Tier 2, higher accuracy)
-- Bayou parsing is async, so bayou_bill_id + a 'parsing' status let the queue
-- poll for the result. Additive columns; no existing data affected.

ALTER TABLE s1_ocr_extraction
    ADD COLUMN IF NOT EXISTS parser TEXT NOT NULL DEFAULT 'claude',   -- claude|bayou
    ADD COLUMN IF NOT EXISTS bayou_bill_id TEXT;
