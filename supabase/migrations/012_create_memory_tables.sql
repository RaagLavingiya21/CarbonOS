-- Semantic memory (user-level and org-level) for platform chat agent

CREATE TABLE IF NOT EXISTS user_memory (
    memory_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    category    TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_memory_user_id ON user_memory (user_id);

CREATE TABLE IF NOT EXISTS org_memory (
    memory_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    created_by  UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    category    TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_org_memory_org_id ON org_memory (org_id);
