-- Tokenized public share links for published footprints (Wave 2 Workstream S)

CREATE TABLE IF NOT EXISTS footprint_shares (
    share_id        BIGSERIAL PRIMARY KEY,
    share_token     TEXT UNIQUE NOT NULL,
    product_id      BIGINT NOT NULL REFERENCES products (product_id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    recipient_label TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_footprint_shares_token ON footprint_shares (share_token);
CREATE INDEX IF NOT EXISTS idx_footprint_shares_product_id ON footprint_shares (product_id);
CREATE INDEX IF NOT EXISTS idx_footprint_shares_user_id ON footprint_shares (user_id);

ALTER TABLE footprint_shares ENABLE ROW LEVEL SECURITY;

CREATE POLICY footprint_shares_select_own ON footprint_shares
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY footprint_shares_insert_own ON footprint_shares
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY footprint_shares_update_own ON footprint_shares
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY footprint_shares_delete_own ON footprint_shares
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);
