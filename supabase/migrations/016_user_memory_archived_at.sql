-- Soft archive support for user semantic memory (10 active memory cap)

ALTER TABLE user_memory
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_user_memory_active
    ON user_memory (user_id, created_at)
    WHERE archived_at IS NULL;
