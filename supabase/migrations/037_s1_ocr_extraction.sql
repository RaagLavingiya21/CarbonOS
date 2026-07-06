-- Scope 1 module (Phase 2): OCR review queue.
-- Each uploaded bill/invoice runs through the LangGraph OCR extraction graph
-- (extract -> confidence-gate -> human review). This table is the queryable
-- index of that workflow: it mirrors the graph phase in `status`, links the
-- evidence document, and records the applied emission record once approved.
-- The graph's own run state lives in the LangGraph Postgres checkpointer
-- (keyed by graph_session_id); this row makes the queue listable + RLS-scoped.

CREATE TABLE IF NOT EXISTS s1_ocr_extraction (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id          UUID REFERENCES s1_inventory (id) ON DELETE SET NULL,
    evidence_document_id  UUID REFERENCES s1_evidence_document (id) ON DELETE SET NULL,
    graph_session_id      TEXT NOT NULL,                     -- LangGraph thread_id
    doc_kind              TEXT NOT NULL,                     -- utility_bill|fuel_invoice
    extracted             JSONB NOT NULL,                    -- {field: {value, confidence}}
    min_confidence        NUMERIC(4,3),
    status                TEXT NOT NULL DEFAULT 'pending_review', -- pending_review|approved|applied|rejected
    applied_record_id     UUID REFERENCES s1_emission_record (id) ON DELETE SET NULL,
    created_by            UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_ocr_org_id ON s1_ocr_extraction (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_ocr_status ON s1_ocr_extraction (org_id, status);

ALTER TABLE s1_ocr_extraction ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_ocr_select_org ON s1_ocr_extraction;
CREATE POLICY s1_ocr_select_org ON s1_ocr_extraction
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_ocr_insert_org ON s1_ocr_extraction;
CREATE POLICY s1_ocr_insert_org ON s1_ocr_extraction
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_ocr_update_org ON s1_ocr_extraction;
CREATE POLICY s1_ocr_update_org ON s1_ocr_extraction
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
