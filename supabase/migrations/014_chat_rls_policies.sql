-- Row-Level Security for platform chat agent tables.
-- Uses is_org_member() helper to avoid infinite recursion on org_members policies.

CREATE OR REPLACE FUNCTION public.is_org_member(target_org_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM org_members
        WHERE org_id = target_org_id
          AND user_id = auth.uid()
    );
$$;

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_threads ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE active_panels ENABLE ROW LEVEL SECURITY;

-- organizations
CREATE POLICY organizations_select_member ON organizations
    FOR SELECT TO authenticated
    USING (public.is_org_member(id));

CREATE POLICY organizations_insert_authenticated ON organizations
    FOR INSERT TO authenticated
    WITH CHECK (true);

CREATE POLICY organizations_update_member ON organizations
    FOR UPDATE TO authenticated
    USING (public.is_org_member(id))
    WITH CHECK (public.is_org_member(id));

CREATE POLICY organizations_delete_member ON organizations
    FOR DELETE TO authenticated
    USING (public.is_org_member(id));

-- org_members
CREATE POLICY org_members_select_member ON org_members
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

CREATE POLICY org_members_insert_self_or_member ON org_members
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid() OR public.is_org_member(org_id));

CREATE POLICY org_members_delete_self_or_member ON org_members
    FOR DELETE TO authenticated
    USING (user_id = auth.uid() OR public.is_org_member(org_id));

-- chat_threads
CREATE POLICY chat_threads_select_own ON chat_threads
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY chat_threads_insert_own ON chat_threads
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY chat_threads_update_own ON chat_threads
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY chat_threads_delete_own ON chat_threads
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- chat_messages (scoped through thread ownership)
CREATE POLICY chat_messages_select_own_thread ON chat_messages
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM chat_threads t
            WHERE t.thread_id = chat_messages.thread_id
              AND t.user_id = auth.uid()
        )
    );

CREATE POLICY chat_messages_insert_own_thread ON chat_messages
    FOR INSERT TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM chat_threads t
            WHERE t.thread_id = chat_messages.thread_id
              AND t.user_id = auth.uid()
        )
    );

CREATE POLICY chat_messages_update_own_thread ON chat_messages
    FOR UPDATE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM chat_threads t
            WHERE t.thread_id = chat_messages.thread_id
              AND t.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1
            FROM chat_threads t
            WHERE t.thread_id = chat_messages.thread_id
              AND t.user_id = auth.uid()
        )
    );

CREATE POLICY chat_messages_delete_own_thread ON chat_messages
    FOR DELETE TO authenticated
    USING (
        EXISTS (
            SELECT 1
            FROM chat_threads t
            WHERE t.thread_id = chat_messages.thread_id
              AND t.user_id = auth.uid()
        )
    );

-- user_memory
CREATE POLICY user_memory_select_own ON user_memory
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY user_memory_insert_own ON user_memory
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_memory_update_own ON user_memory
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY user_memory_delete_own ON user_memory
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- org_memory
CREATE POLICY org_memory_select_member ON org_memory
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

CREATE POLICY org_memory_insert_member ON org_memory
    FOR INSERT TO authenticated
    WITH CHECK (
        public.is_org_member(org_id)
        AND created_by = auth.uid()
    );

CREATE POLICY org_memory_update_member ON org_memory
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

CREATE POLICY org_memory_delete_member ON org_memory
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- active_panels
CREATE POLICY active_panels_select_own ON active_panels
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY active_panels_insert_own ON active_panels
    FOR INSERT TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY active_panels_update_own ON active_panels
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY active_panels_delete_own ON active_panels
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);
