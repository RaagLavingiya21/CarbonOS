-- Org-wide read visibility for products and line_items.
-- Teammates in the same org can SELECT each other's rows; writes remain owner-only.

CREATE OR REPLACE FUNCTION public.shares_org_with(target_user_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM org_members me
        JOIN org_members them ON me.org_id = them.org_id
        WHERE me.user_id = auth.uid()
          AND them.user_id = target_user_id
    );
$$;

CREATE POLICY products_select_org ON products
    FOR SELECT TO authenticated
    USING (public.shares_org_with(user_id));

CREATE POLICY line_items_select_org ON line_items
    FOR SELECT TO authenticated
    USING (public.shares_org_with(user_id));
