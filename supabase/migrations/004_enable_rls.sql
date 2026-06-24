-- Row-Level Security: each authenticated user sees only their own data.
-- suppliers is shared reference data readable by all authenticated users.

ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE line_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE engagements ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- products
CREATE POLICY products_select_own ON products
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY products_insert_own ON products
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY products_update_own ON products
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY products_delete_own ON products
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- line_items
CREATE POLICY line_items_select_own ON line_items
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY line_items_insert_own ON line_items
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY line_items_update_own ON line_items
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY line_items_delete_own ON line_items
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- suppliers (shared read-only for authenticated users)
CREATE POLICY suppliers_select_authenticated ON suppliers
    FOR SELECT TO authenticated
    USING (true);

-- engagements
CREATE POLICY engagements_select_own ON engagements
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY engagements_insert_own ON engagements
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY engagements_update_own ON engagements
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY engagements_delete_own ON engagements
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- audit_log
CREATE POLICY audit_log_select_own ON audit_log
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY audit_log_insert_own ON audit_log
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY audit_log_update_own ON audit_log
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY audit_log_delete_own ON audit_log
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);
