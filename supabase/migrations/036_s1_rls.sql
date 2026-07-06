-- Scope 1 module (isolated): Row-Level Security for all s1_ tables.
-- Org-scoped tables reuse the existing public.is_org_member(org_id) helper
-- (defined in 014_chat_rls_policies.sql) so a user only ever sees rows for orgs
-- they belong to. Append-only tables get SELECT + INSERT only (no UPDATE/DELETE
-- policy => default-deny => immutable). Reference tables are world-readable to
-- authenticated users; writes happen only via the service role (seed script),
-- which bypasses RLS.

-- =====================================================================
-- Org-scoped tables — full CRUD for org members
-- =====================================================================

-- s1_legal_entity
ALTER TABLE s1_legal_entity ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_legal_entity_select_org ON s1_legal_entity;
CREATE POLICY s1_legal_entity_select_org ON s1_legal_entity
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_legal_entity_insert_org ON s1_legal_entity;
CREATE POLICY s1_legal_entity_insert_org ON s1_legal_entity
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_legal_entity_update_org ON s1_legal_entity;
CREATE POLICY s1_legal_entity_update_org ON s1_legal_entity
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_legal_entity_delete_org ON s1_legal_entity;
CREATE POLICY s1_legal_entity_delete_org ON s1_legal_entity
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_entity_hierarchy_path
ALTER TABLE s1_entity_hierarchy_path ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_entity_path_select_org ON s1_entity_hierarchy_path;
CREATE POLICY s1_entity_path_select_org ON s1_entity_hierarchy_path
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_entity_path_insert_org ON s1_entity_hierarchy_path;
CREATE POLICY s1_entity_path_insert_org ON s1_entity_hierarchy_path
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_entity_path_update_org ON s1_entity_hierarchy_path;
CREATE POLICY s1_entity_path_update_org ON s1_entity_hierarchy_path
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_entity_path_delete_org ON s1_entity_hierarchy_path;
CREATE POLICY s1_entity_path_delete_org ON s1_entity_hierarchy_path
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_facility
ALTER TABLE s1_facility ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_facility_select_org ON s1_facility;
CREATE POLICY s1_facility_select_org ON s1_facility
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_facility_insert_org ON s1_facility;
CREATE POLICY s1_facility_insert_org ON s1_facility
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_facility_update_org ON s1_facility;
CREATE POLICY s1_facility_update_org ON s1_facility
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_facility_delete_org ON s1_facility;
CREATE POLICY s1_facility_delete_org ON s1_facility
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_inventory
ALTER TABLE s1_inventory ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_inventory_select_org ON s1_inventory;
CREATE POLICY s1_inventory_select_org ON s1_inventory
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_inventory_insert_org ON s1_inventory;
CREATE POLICY s1_inventory_insert_org ON s1_inventory
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_inventory_update_org ON s1_inventory;
CREATE POLICY s1_inventory_update_org ON s1_inventory
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_inventory_delete_org ON s1_inventory;
CREATE POLICY s1_inventory_delete_org ON s1_inventory
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_inventory_entity_boundary
ALTER TABLE s1_inventory_entity_boundary ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_boundary_select_org ON s1_inventory_entity_boundary;
CREATE POLICY s1_boundary_select_org ON s1_inventory_entity_boundary
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_boundary_insert_org ON s1_inventory_entity_boundary;
CREATE POLICY s1_boundary_insert_org ON s1_inventory_entity_boundary
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_boundary_update_org ON s1_inventory_entity_boundary;
CREATE POLICY s1_boundary_update_org ON s1_inventory_entity_boundary
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_boundary_delete_org ON s1_inventory_entity_boundary;
CREATE POLICY s1_boundary_delete_org ON s1_inventory_entity_boundary
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_emission_source
ALTER TABLE s1_emission_source ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_source_select_org ON s1_emission_source;
CREATE POLICY s1_source_select_org ON s1_emission_source
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_source_insert_org ON s1_emission_source;
CREATE POLICY s1_source_insert_org ON s1_emission_source
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_source_update_org ON s1_emission_source;
CREATE POLICY s1_source_update_org ON s1_emission_source
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_source_delete_org ON s1_emission_source;
CREATE POLICY s1_source_delete_org ON s1_emission_source
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_emission_record
ALTER TABLE s1_emission_record ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_record_select_org ON s1_emission_record;
CREATE POLICY s1_record_select_org ON s1_emission_record
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_record_insert_org ON s1_emission_record;
CREATE POLICY s1_record_insert_org ON s1_emission_record
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_record_update_org ON s1_emission_record;
CREATE POLICY s1_record_update_org ON s1_emission_record
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_record_delete_org ON s1_emission_record;
CREATE POLICY s1_record_delete_org ON s1_emission_record
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_emission_record_gas_detail
ALTER TABLE s1_emission_record_gas_detail ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_gas_detail_select_org ON s1_emission_record_gas_detail;
CREATE POLICY s1_gas_detail_select_org ON s1_emission_record_gas_detail
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_gas_detail_insert_org ON s1_emission_record_gas_detail;
CREATE POLICY s1_gas_detail_insert_org ON s1_emission_record_gas_detail
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_gas_detail_update_org ON s1_emission_record_gas_detail;
CREATE POLICY s1_gas_detail_update_org ON s1_emission_record_gas_detail
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_gas_detail_delete_org ON s1_emission_record_gas_detail;
CREATE POLICY s1_gas_detail_delete_org ON s1_emission_record_gas_detail
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_data_owner
ALTER TABLE s1_data_owner ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_data_owner_select_org ON s1_data_owner;
CREATE POLICY s1_data_owner_select_org ON s1_data_owner
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_data_owner_insert_org ON s1_data_owner;
CREATE POLICY s1_data_owner_insert_org ON s1_data_owner
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_data_owner_update_org ON s1_data_owner;
CREATE POLICY s1_data_owner_update_org ON s1_data_owner
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_data_owner_delete_org ON s1_data_owner;
CREATE POLICY s1_data_owner_delete_org ON s1_data_owner
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_source_data_owner
ALTER TABLE s1_source_data_owner ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_source_owner_select_org ON s1_source_data_owner;
CREATE POLICY s1_source_owner_select_org ON s1_source_data_owner
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_source_owner_insert_org ON s1_source_data_owner;
CREATE POLICY s1_source_owner_insert_org ON s1_source_data_owner
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_source_owner_update_org ON s1_source_data_owner;
CREATE POLICY s1_source_owner_update_org ON s1_source_data_owner
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_source_owner_delete_org ON s1_source_data_owner;
CREATE POLICY s1_source_owner_delete_org ON s1_source_data_owner
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_source_collection_status
ALTER TABLE s1_source_collection_status ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_collection_select_org ON s1_source_collection_status;
CREATE POLICY s1_collection_select_org ON s1_source_collection_status
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_collection_insert_org ON s1_source_collection_status;
CREATE POLICY s1_collection_insert_org ON s1_source_collection_status
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_collection_update_org ON s1_source_collection_status;
CREATE POLICY s1_collection_update_org ON s1_source_collection_status
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_collection_delete_org ON s1_source_collection_status;
CREATE POLICY s1_collection_delete_org ON s1_source_collection_status
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));

-- s1_evidence_document (soft-delete only; UPDATE allowed to set deleted_at)
ALTER TABLE s1_evidence_document ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_evidence_select_org ON s1_evidence_document;
CREATE POLICY s1_evidence_select_org ON s1_evidence_document
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_evidence_insert_org ON s1_evidence_document;
CREATE POLICY s1_evidence_insert_org ON s1_evidence_document
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_evidence_update_org ON s1_evidence_document;
CREATE POLICY s1_evidence_update_org ON s1_evidence_document
    FOR UPDATE TO authenticated USING (public.is_org_member(org_id)) WITH CHECK (public.is_org_member(org_id));

-- =====================================================================
-- Append-only tables — SELECT + INSERT only (no UPDATE/DELETE => immutable)
-- =====================================================================

-- s1_boundary_decision_log
ALTER TABLE s1_boundary_decision_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_boundary_log_select_org ON s1_boundary_decision_log;
CREATE POLICY s1_boundary_log_select_org ON s1_boundary_decision_log
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_boundary_log_insert_org ON s1_boundary_decision_log;
CREATE POLICY s1_boundary_log_insert_org ON s1_boundary_decision_log
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));

-- s1_change_log
ALTER TABLE s1_change_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_change_log_select_org ON s1_change_log;
CREATE POLICY s1_change_log_select_org ON s1_change_log
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));
DROP POLICY IF EXISTS s1_change_log_insert_org ON s1_change_log;
CREATE POLICY s1_change_log_insert_org ON s1_change_log
    FOR INSERT TO authenticated WITH CHECK (public.is_org_member(org_id));

-- =====================================================================
-- Reference tables — world-readable to authenticated; writes via service role
-- =====================================================================

ALTER TABLE s1_gas_species ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_gas_species_select_authenticated ON s1_gas_species;
CREATE POLICY s1_gas_species_select_authenticated ON s1_gas_species
    FOR SELECT TO authenticated USING (true);

ALTER TABLE s1_gas_blend_component ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_gas_blend_select_authenticated ON s1_gas_blend_component;
CREATE POLICY s1_gas_blend_select_authenticated ON s1_gas_blend_component
    FOR SELECT TO authenticated USING (true);

ALTER TABLE s1_gwp_version ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_gwp_version_select_authenticated ON s1_gwp_version;
CREATE POLICY s1_gwp_version_select_authenticated ON s1_gwp_version
    FOR SELECT TO authenticated USING (true);

ALTER TABLE s1_gwp_value ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_gwp_value_select_authenticated ON s1_gwp_value;
CREATE POLICY s1_gwp_value_select_authenticated ON s1_gwp_value
    FOR SELECT TO authenticated USING (true);

ALTER TABLE s1_ef_record ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_ef_record_select_authenticated ON s1_ef_record;
CREATE POLICY s1_ef_record_select_authenticated ON s1_ef_record
    FOR SELECT TO authenticated USING (true);

ALTER TABLE s1_reporting_regime_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS s1_regime_config_select_authenticated ON s1_reporting_regime_config;
CREATE POLICY s1_regime_config_select_authenticated ON s1_reporting_regime_config
    FOR SELECT TO authenticated USING (true);
