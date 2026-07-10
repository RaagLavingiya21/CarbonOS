-- Scope 1 — RLS-hard role enforcement (defense in depth).
--
-- Until now Scope-1 roles (admin/editor/viewer) were enforced only in the app
-- layer; the DB's write policies checked bare is_org_member(org_id), so a viewer
-- using the Supabase anon key + their JWT could write directly, bypassing the
-- backend. This migration moves the role check into the database:
--   * s1_can_edit(org_id): org member AND resolved role != viewer  (editor+)
--   * s1_is_admin(org_id): resolved role == admin
-- resolving roles exactly like the app (explicit s1_member_role row wins; else
-- org_members.role='admin' -> admin, else editor). SELECT policies are unchanged
-- (viewers keep read access). App-layer checks stay as fast-fail + good UX.
--
-- Idempotent: CREATE OR REPLACE FUNCTION + DROP POLICY IF EXISTS before CREATE.
-- Band: Scope 1 = 110-199.

CREATE OR REPLACE FUNCTION public.s1_can_edit(target_org_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT public.is_org_member(target_org_id)
       AND NOT EXISTS (
           SELECT 1 FROM s1_member_role
           WHERE org_id = target_org_id AND user_id = auth.uid() AND role = 'viewer'
       );
$$;

CREATE OR REPLACE FUNCTION public.s1_is_admin(target_org_id uuid)
RETURNS boolean
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
STABLE
AS $$
    SELECT public.is_org_member(target_org_id)
       AND (
           EXISTS (
               SELECT 1 FROM s1_member_role
               WHERE org_id = target_org_id AND user_id = auth.uid() AND role = 'admin'
           )
           OR (
               NOT EXISTS (
                   SELECT 1 FROM s1_member_role
                   WHERE org_id = target_org_id AND user_id = auth.uid()
               )
               AND EXISTS (
                   SELECT 1 FROM org_members
                   WHERE org_id = target_org_id AND user_id = auth.uid() AND role = 'admin'
               )
           )
       );
$$;


-- s1_base_year_recalc_event  (s1_can_edit)
DROP POLICY IF EXISTS s1_recalc_event_delete_org ON s1_base_year_recalc_event;
CREATE POLICY s1_recalc_event_delete_org ON s1_base_year_recalc_event
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_recalc_event_insert_org ON s1_base_year_recalc_event;
CREATE POLICY s1_recalc_event_insert_org ON s1_base_year_recalc_event
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_recalc_event_update_org ON s1_base_year_recalc_event;
CREATE POLICY s1_recalc_event_update_org ON s1_base_year_recalc_event
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_boundary_decision_log  (s1_can_edit)
DROP POLICY IF EXISTS s1_boundary_log_insert_org ON s1_boundary_decision_log;
CREATE POLICY s1_boundary_log_insert_org ON s1_boundary_decision_log
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));

-- s1_change_log  (s1_can_edit)
DROP POLICY IF EXISTS s1_change_log_insert_org ON s1_change_log;
CREATE POLICY s1_change_log_insert_org ON s1_change_log
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));

-- s1_data_owner  (s1_can_edit)
DROP POLICY IF EXISTS s1_data_owner_delete_org ON s1_data_owner;
CREATE POLICY s1_data_owner_delete_org ON s1_data_owner
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_data_owner_insert_org ON s1_data_owner;
CREATE POLICY s1_data_owner_insert_org ON s1_data_owner
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_data_owner_update_org ON s1_data_owner;
CREATE POLICY s1_data_owner_update_org ON s1_data_owner
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_ef_override  (s1_is_admin)
DROP POLICY IF EXISTS s1_ef_override_delete_org ON s1_ef_override;
CREATE POLICY s1_ef_override_delete_org ON s1_ef_override
    FOR DELETE TO authenticated USING (public.s1_is_admin(org_id));
DROP POLICY IF EXISTS s1_ef_override_insert_org ON s1_ef_override;
CREATE POLICY s1_ef_override_insert_org ON s1_ef_override
    FOR INSERT TO authenticated WITH CHECK (public.s1_is_admin(org_id));
DROP POLICY IF EXISTS s1_ef_override_update_org ON s1_ef_override;
CREATE POLICY s1_ef_override_update_org ON s1_ef_override
    FOR UPDATE TO authenticated USING (public.s1_is_admin(org_id)) WITH CHECK (public.s1_is_admin(org_id));

-- s1_emission_record  (s1_can_edit)
DROP POLICY IF EXISTS s1_record_delete_org ON s1_emission_record;
CREATE POLICY s1_record_delete_org ON s1_emission_record
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_record_insert_org ON s1_emission_record;
CREATE POLICY s1_record_insert_org ON s1_emission_record
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_record_update_org ON s1_emission_record;
CREATE POLICY s1_record_update_org ON s1_emission_record
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_emission_record_gas_detail  (s1_can_edit)
DROP POLICY IF EXISTS s1_gas_detail_delete_org ON s1_emission_record_gas_detail;
CREATE POLICY s1_gas_detail_delete_org ON s1_emission_record_gas_detail
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_gas_detail_insert_org ON s1_emission_record_gas_detail;
CREATE POLICY s1_gas_detail_insert_org ON s1_emission_record_gas_detail
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_gas_detail_update_org ON s1_emission_record_gas_detail;
CREATE POLICY s1_gas_detail_update_org ON s1_emission_record_gas_detail
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_emission_source  (s1_can_edit)
DROP POLICY IF EXISTS s1_source_delete_org ON s1_emission_source;
CREATE POLICY s1_source_delete_org ON s1_emission_source
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_source_insert_org ON s1_emission_source;
CREATE POLICY s1_source_insert_org ON s1_emission_source
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_source_update_org ON s1_emission_source;
CREATE POLICY s1_source_update_org ON s1_emission_source
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_entity_hierarchy_path  (s1_can_edit)
DROP POLICY IF EXISTS s1_entity_path_delete_org ON s1_entity_hierarchy_path;
CREATE POLICY s1_entity_path_delete_org ON s1_entity_hierarchy_path
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_entity_path_insert_org ON s1_entity_hierarchy_path;
CREATE POLICY s1_entity_path_insert_org ON s1_entity_hierarchy_path
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_entity_path_update_org ON s1_entity_hierarchy_path;
CREATE POLICY s1_entity_path_update_org ON s1_entity_hierarchy_path
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_evidence_document  (s1_can_edit)
DROP POLICY IF EXISTS s1_evidence_insert_org ON s1_evidence_document;
CREATE POLICY s1_evidence_insert_org ON s1_evidence_document
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_evidence_update_org ON s1_evidence_document;
CREATE POLICY s1_evidence_update_org ON s1_evidence_document
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_facility  (s1_can_edit)
DROP POLICY IF EXISTS s1_facility_delete_org ON s1_facility;
CREATE POLICY s1_facility_delete_org ON s1_facility
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_facility_insert_org ON s1_facility;
CREATE POLICY s1_facility_insert_org ON s1_facility
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_facility_update_org ON s1_facility;
CREATE POLICY s1_facility_update_org ON s1_facility
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_fugitive_record  (s1_can_edit)
DROP POLICY IF EXISTS s1_fugitive_delete_org ON s1_fugitive_record;
CREATE POLICY s1_fugitive_delete_org ON s1_fugitive_record
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_fugitive_insert_org ON s1_fugitive_record;
CREATE POLICY s1_fugitive_insert_org ON s1_fugitive_record
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_fugitive_update_org ON s1_fugitive_record;
CREATE POLICY s1_fugitive_update_org ON s1_fugitive_record
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_inventory  (s1_can_edit)
DROP POLICY IF EXISTS s1_inventory_delete_org ON s1_inventory;
CREATE POLICY s1_inventory_delete_org ON s1_inventory
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_inventory_insert_org ON s1_inventory;
CREATE POLICY s1_inventory_insert_org ON s1_inventory
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_inventory_update_org ON s1_inventory;
CREATE POLICY s1_inventory_update_org ON s1_inventory
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_inventory_entity_boundary  (s1_can_edit)
DROP POLICY IF EXISTS s1_boundary_delete_org ON s1_inventory_entity_boundary;
CREATE POLICY s1_boundary_delete_org ON s1_inventory_entity_boundary
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_boundary_insert_org ON s1_inventory_entity_boundary;
CREATE POLICY s1_boundary_insert_org ON s1_inventory_entity_boundary
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_boundary_update_org ON s1_inventory_entity_boundary;
CREATE POLICY s1_boundary_update_org ON s1_inventory_entity_boundary
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_legal_entity  (s1_can_edit)
DROP POLICY IF EXISTS s1_legal_entity_delete_org ON s1_legal_entity;
CREATE POLICY s1_legal_entity_delete_org ON s1_legal_entity
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_legal_entity_insert_org ON s1_legal_entity;
CREATE POLICY s1_legal_entity_insert_org ON s1_legal_entity
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_legal_entity_update_org ON s1_legal_entity;
CREATE POLICY s1_legal_entity_update_org ON s1_legal_entity
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_member_role  (s1_is_admin)
DROP POLICY IF EXISTS s1_member_role_delete_org ON s1_member_role;
CREATE POLICY s1_member_role_delete_org ON s1_member_role
    FOR DELETE TO authenticated USING (public.s1_is_admin(org_id));
DROP POLICY IF EXISTS s1_member_role_insert_org ON s1_member_role;
CREATE POLICY s1_member_role_insert_org ON s1_member_role
    FOR INSERT TO authenticated WITH CHECK (public.s1_is_admin(org_id));
DROP POLICY IF EXISTS s1_member_role_update_org ON s1_member_role;
CREATE POLICY s1_member_role_update_org ON s1_member_role
    FOR UPDATE TO authenticated USING (public.s1_is_admin(org_id)) WITH CHECK (public.s1_is_admin(org_id));

-- s1_ocr_extraction  (s1_can_edit)
DROP POLICY IF EXISTS s1_ocr_insert_org ON s1_ocr_extraction;
CREATE POLICY s1_ocr_insert_org ON s1_ocr_extraction
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_ocr_update_org ON s1_ocr_extraction;
CREATE POLICY s1_ocr_update_org ON s1_ocr_extraction
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_process_record  (s1_can_edit)
DROP POLICY IF EXISTS s1_process_delete_org ON s1_process_record;
CREATE POLICY s1_process_delete_org ON s1_process_record
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_process_insert_org ON s1_process_record;
CREATE POLICY s1_process_insert_org ON s1_process_record
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_process_update_org ON s1_process_record;
CREATE POLICY s1_process_update_org ON s1_process_record
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_source_collection_status  (s1_can_edit)
DROP POLICY IF EXISTS s1_collection_delete_org ON s1_source_collection_status;
CREATE POLICY s1_collection_delete_org ON s1_source_collection_status
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_collection_insert_org ON s1_source_collection_status;
CREATE POLICY s1_collection_insert_org ON s1_source_collection_status
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_collection_update_org ON s1_source_collection_status;
CREATE POLICY s1_collection_update_org ON s1_source_collection_status
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));

-- s1_source_data_owner  (s1_can_edit)
DROP POLICY IF EXISTS s1_source_owner_delete_org ON s1_source_data_owner;
CREATE POLICY s1_source_owner_delete_org ON s1_source_data_owner
    FOR DELETE TO authenticated USING (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_source_owner_insert_org ON s1_source_data_owner;
CREATE POLICY s1_source_owner_insert_org ON s1_source_data_owner
    FOR INSERT TO authenticated WITH CHECK (public.s1_can_edit(org_id));
DROP POLICY IF EXISTS s1_source_owner_update_org ON s1_source_data_owner;
CREATE POLICY s1_source_owner_update_org ON s1_source_data_owner
    FOR UPDATE TO authenticated USING (public.s1_can_edit(org_id)) WITH CHECK (public.s1_can_edit(org_id));
