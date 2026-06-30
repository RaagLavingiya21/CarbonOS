-- Soft delete support for chat threads

ALTER TABLE chat_threads
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_chat_threads_deleted_at
    ON chat_threads (deleted_at)
    WHERE deleted_at IS NULL;
