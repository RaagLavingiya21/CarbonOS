-- Append-only audit trail for supplier engagement workflows (user-owned)

CREATE TABLE IF NOT EXISTS audit_log (
    log_id                BIGSERIAL PRIMARY KEY,
    user_id               UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    timestamp             TIMESTAMPTZ NOT NULL DEFAULT now(),
    event                 TEXT NOT NULL,
    workflow              TEXT NOT NULL,
    model                 TEXT,
    supplier_name         TEXT,
    product_name          TEXT,
    component_name        TEXT,
    email_sent            TEXT,
    response_received     TEXT,
    routing_decision      TEXT,
    decision_rationale    TEXT,
    ghg_protocol_citation TEXT,
    data_collected        TEXT,
    status                TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_supplier ON audit_log (user_id, supplier_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_product ON audit_log (user_id, product_name);
