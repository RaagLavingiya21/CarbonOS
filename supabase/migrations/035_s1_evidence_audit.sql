-- Scope 1 module (isolated): immutable evidence + append-only change log.
-- Evidence bytes live in the Supabase Storage bucket `s1-evidence`; this table
-- holds the metadata + a server-computed SHA-256 for tamper evidence. Soft-delete
-- only. This is the substrate for the "View Source" panel and future assurance.
-- See research/2.3 section B4 and 2.2 C2.

CREATE TABLE IF NOT EXISTS s1_evidence_document (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id   UUID REFERENCES s1_inventory (id) ON DELETE SET NULL,
    document_type  TEXT NOT NULL,                              -- utility_invoice|fuel_invoice|meter_reading|fuel_card_report|third_party_report|api_json|manual_note
    file_name      TEXT,
    storage_uri    TEXT NOT NULL,                              -- path in the s1-evidence bucket: {org_id}/{inventory_id}/{record_id}/{filename}
    content_type   TEXT,
    byte_size      BIGINT,
    hash_sha256    TEXT NOT NULL,                              -- computed server-side; tamper evidence
    uploaded_by    UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    uploaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ                                 -- soft-delete only
);

CREATE INDEX IF NOT EXISTS idx_s1_evidence_org_id ON s1_evidence_document (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_evidence_inventory ON s1_evidence_document (inventory_id);

-- Deferred FK: emission_record.evidence_document_id -> evidence_document.id.
-- Wrapped so re-running the migration is idempotent (ADD CONSTRAINT has no IF NOT EXISTS).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 's1_emission_record_evidence_fk'
    ) THEN
        ALTER TABLE s1_emission_record
            ADD CONSTRAINT s1_emission_record_evidence_fk
            FOREIGN KEY (evidence_document_id)
            REFERENCES s1_evidence_document (id) ON DELETE SET NULL;
    END IF;
END $$;

-- Append-only change log per record (immutable audit trail). No UPDATE/DELETE
-- (enforced in RLS migration 036).
CREATE TABLE IF NOT EXISTS s1_change_log (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    entity_table   TEXT NOT NULL,                              -- s1_emission_record|s1_inventory|s1_emission_source|...
    entity_id      UUID NOT NULL,
    action         TEXT NOT NULL,                              -- create|update|lock|exclude|correct|delete
    field_changes  JSONB,                                      -- {field: {from, to}}
    actor_id       UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_change_log_org_id ON s1_change_log (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_change_log_entity ON s1_change_log (entity_table, entity_id);
