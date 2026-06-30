-- Active module panels (persisted across page refresh)

CREATE TABLE IF NOT EXISTS active_panels (
    panel_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    thread_id   UUID REFERENCES chat_threads (thread_id) ON DELETE SET NULL,
    module_type TEXT NOT NULL,
    panel_state JSONB NOT NULL DEFAULT '{}',
    tab_order   INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_active_panels_user_id ON active_panels (user_id);
CREATE INDEX IF NOT EXISTS idx_active_panels_thread_id ON active_panels (thread_id);
