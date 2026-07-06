-- Scope 1 module (isolated): the data-owner network + per-source collection
-- status. This is the core-value layer — it answers "who supplies each source's
-- data" and "what's still missing", driving the readiness / completeness meter
-- that kills the Q1 scramble. See MVP-PRD.md job P3 and research/3.5.

-- People/orgs who supply activity data (facility mgr, fleet admin, procurement,
-- landlord, lessor, contractor). Distinct from the legal-entity tree.
CREATE TABLE IF NOT EXISTS s1_data_owner (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    email         TEXT,
    role_title    TEXT,                                        -- facility_manager|fleet_admin|procurement|landlord|lessor|contractor
    owner_type    TEXT NOT NULL DEFAULT 'internal',           -- internal|third_party
    user_id       UUID REFERENCES auth.users (id) ON DELETE SET NULL,  -- if they have a platform login
    created_by    UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s1_data_owner_org_id ON s1_data_owner (org_id);

-- Which owner supplies which source's data (the network mapping).
CREATE TABLE IF NOT EXISTS s1_source_data_owner (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    emission_source_id UUID NOT NULL REFERENCES s1_emission_source (id) ON DELETE CASCADE,
    data_owner_id      UUID NOT NULL REFERENCES s1_data_owner (id) ON DELETE CASCADE,
    assigned_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (emission_source_id, data_owner_id)
);

CREATE INDEX IF NOT EXISTS idx_s1_source_owner_org_id ON s1_source_data_owner (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_source_owner_source ON s1_source_data_owner (emission_source_id);

-- Per source x period collection status -> drives the readiness meter.
CREATE TABLE IF NOT EXISTS s1_source_collection_status (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    inventory_id       UUID NOT NULL REFERENCES s1_inventory (id) ON DELETE CASCADE,
    emission_source_id UUID NOT NULL REFERENCES s1_emission_source (id) ON DELETE CASCADE,
    period_start       DATE NOT NULL,
    period_end         DATE NOT NULL,
    status             TEXT NOT NULL DEFAULT 'missing',        -- missing|requested|in_progress|received|entered|verified
    data_owner_id      UUID REFERENCES s1_data_owner (id) ON DELETE SET NULL,
    notes              TEXT,
    updated_by         UUID REFERENCES auth.users (id) ON DELETE SET NULL,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (inventory_id, emission_source_id, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_s1_collection_org_id ON s1_source_collection_status (org_id);
CREATE INDEX IF NOT EXISTS idx_s1_collection_inventory ON s1_source_collection_status (inventory_id);
