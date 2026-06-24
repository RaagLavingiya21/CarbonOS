-- Shared supplier directory and user-owned engagement records

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id   BIGSERIAL PRIMARY KEY,
    supplier_name TEXT NOT NULL UNIQUE,
    contact_name  TEXT,
    contact_email TEXT
);

INSERT INTO suppliers (supplier_name, contact_name, contact_email)
VALUES
    ('FiberTex Global', 'Sarah Chen', 'sarah.chen@fibertex.example.com'),
    ('PolyNova Materials', 'Raj Patel', 'raj.patel@polynova.example.com'),
    ('ChemDyes International', 'Maria Santos', 'maria.santos@chemdyes.example.com'),
    ('PackRight Solutions', 'Tom Eriksson', 'tom.eriksson@packright.example.com'),
    ('MetalWorks Industries', 'Aisha Okonkwo', 'aisha.okonkwo@metalworks.example.com'),
    ('SilicaSoft Technologies', 'James Liu', 'james.liu@silicasoft.example.com')
ON CONFLICT (supplier_name) DO NOTHING;

CREATE TABLE IF NOT EXISTS engagements (
    engagement_id         BIGSERIAL PRIMARY KEY,
    user_id               UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    supplier_name         TEXT NOT NULL,
    product_name          TEXT NOT NULL,
    component_name        TEXT,
    material              TEXT,
    kg_co2e               DOUBLE PRECISION,
    share_pct             DOUBLE PRECISION,
    status                TEXT NOT NULL DEFAULT 'open',
    email_draft           TEXT,
    email_sent            TEXT,
    response_received     TEXT,
    routing_decision      TEXT,
    decision_rationale    TEXT,
    ghg_protocol_citation TEXT,
    next_step             TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_action_date      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_engagements_user_id ON engagements (user_id);
CREATE INDEX IF NOT EXISTS idx_engagements_product_name ON engagements (user_id, product_name);
CREATE INDEX IF NOT EXISTS idx_engagements_supplier_name ON engagements (user_id, supplier_name);
