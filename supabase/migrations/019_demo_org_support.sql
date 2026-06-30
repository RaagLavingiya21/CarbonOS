-- Demo org flag and per-user active workspace preference.

ALTER TABLE organizations
    ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id         UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    active_org_id   UUID REFERENCES organizations (id) ON DELETE SET NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_preferences_select_own ON user_preferences
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY user_preferences_insert_own ON user_preferences
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_preferences_update_own ON user_preferences
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_preferences_delete_own ON user_preferences
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);
