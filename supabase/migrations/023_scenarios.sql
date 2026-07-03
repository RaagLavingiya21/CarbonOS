CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id            BIGSERIAL PRIMARY KEY,
    user_id                UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    baseline_product_id    BIGINT NOT NULL,
    name                   TEXT NOT NULL,
    baseline_total_kg_co2e DOUBLE PRECISION NOT NULL,
    total_kg_co2e          DOUBLE PRECISION NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS scenario_line_items (
    scenario_item_id  BIGSERIAL PRIMARY KEY,
    scenario_id       BIGINT NOT NULL REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    component         TEXT,
    material          TEXT,
    spend_usd         DOUBLE PRECISION,
    matched_sector    TEXT,
    emission_factor   DOUBLE PRECISION,
    ef_source         TEXT,
    kg_co2e           DOUBLE PRECISION,
    share_pct         DOUBLE PRECISION,
    baseline_material TEXT,
    baseline_kg_co2e  DOUBLE PRECISION,
    is_edited         BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS idx_scenarios_user_id ON scenarios (user_id);
CREATE INDEX IF NOT EXISTS idx_scenarios_baseline ON scenarios (baseline_product_id);
CREATE INDEX IF NOT EXISTS idx_scenario_items_scenario ON scenario_line_items (scenario_id);
CREATE INDEX IF NOT EXISTS idx_scenario_items_user ON scenario_line_items (user_id);

-- Row-Level Security: each authenticated user sees only their own scenario data.
ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE scenario_line_items ENABLE ROW LEVEL SECURITY;

-- scenarios
CREATE POLICY scenarios_select_own ON scenarios
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY scenarios_insert_own ON scenarios
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY scenarios_update_own ON scenarios
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY scenarios_delete_own ON scenarios
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- scenario_line_items
CREATE POLICY scenario_line_items_select_own ON scenario_line_items
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY scenario_line_items_insert_own ON scenario_line_items
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY scenario_line_items_update_own ON scenario_line_items
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY scenario_line_items_delete_own ON scenario_line_items
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);
