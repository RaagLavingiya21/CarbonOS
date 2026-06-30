-- Organizations and org membership for platform chat agent multi-tenancy

CREATE TABLE IF NOT EXISTS organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS org_members (
    user_id     UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    org_id      UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    role        TEXT NOT NULL DEFAULT 'member',
    PRIMARY KEY (user_id, org_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_org_id ON org_members (org_id);
