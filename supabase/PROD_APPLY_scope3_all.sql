-- ============================================================
-- Scope 3 — full production migration bundle
-- Apply once to the PRODUCTION database (Supabase SQL Editor).
-- Ordered 300-317 (contiguous S3 band 300-399). Every statement
-- is idempotent
-- (CREATE TABLE IF NOT EXISTS / DROP POLICY IF EXISTS) so this
-- whole file is safe to re-run. Wrapped in one transaction.
-- Prereqs (already in prod, <=029): organizations, org_members,
-- public.is_org_member(), auth.users.
-- ============================================================

BEGIN;

-- ----------------------------------------------------------
-- 300_inventory_versions.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic A · corporate inventory version (snapshot of a company's
-- Scope 3 inventory for a reporting year). Band 050-059 (Scope 3 lane).
-- Tenancy: org_id is the RLS key via public.is_org_member(org_id) (migration 014).
-- user_id is created_by metadata only and is NEVER referenced in a policy.

CREATE TABLE IF NOT EXISTS s3_inventory_versions (
    inventory_id       BIGSERIAL PRIMARY KEY,
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id            UUID REFERENCES auth.users (id),   -- created_by metadata only
    reporting_year     INTEGER NOT NULL,
    boundary_approach  TEXT NOT NULL DEFAULT 'operational_control'
                       CHECK (boundary_approach IN ('equity', 'financial_control', 'operational_control')),
    status             TEXT NOT NULL DEFAULT 'draft'
                       CHECK (status IN ('draft', 'calculated', 'locked')),
    is_base_year       BOOLEAN NOT NULL DEFAULT false,
    total_kg_co2e      DOUBLE PRECISION,
    version            INTEGER NOT NULL DEFAULT 1,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    locked_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_s3_inventory_versions_org ON s3_inventory_versions (org_id);

ALTER TABLE s3_inventory_versions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_inventory_versions_select ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_select ON s3_inventory_versions
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_versions_insert ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_insert ON s3_inventory_versions
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_versions_update ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_update ON s3_inventory_versions
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_versions_delete ON s3_inventory_versions;
CREATE POLICY s3_inventory_versions_delete ON s3_inventory_versions
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 301_spend_records.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic A · normalized GL/ERP spend lines feeding an inventory version.
-- org_id is carried (denormalized) on every table so RLS is a direct
-- public.is_org_member(org_id) check with no joins.

CREATE TABLE IF NOT EXISTS s3_spend_records (
    spend_record_id  BIGSERIAL PRIMARY KEY,
    inventory_id     BIGINT NOT NULL REFERENCES s3_inventory_versions (inventory_id) ON DELETE CASCADE,
    org_id           UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id          UUID REFERENCES auth.users (id),   -- created_by metadata only
    gl_account       TEXT,
    description      TEXT,
    vendor           TEXT,
    amount_usd       DOUBLE PRECISION,
    currency         TEXT DEFAULT 'USD',
    period           TEXT,
    source_file      TEXT,
    flag_status      TEXT NOT NULL DEFAULT 'ok',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_spend_records_org ON s3_spend_records (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_spend_records_inventory ON s3_spend_records (inventory_id);

ALTER TABLE s3_spend_records ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_spend_records_select ON s3_spend_records;
CREATE POLICY s3_spend_records_select ON s3_spend_records
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_records_insert ON s3_spend_records;
CREATE POLICY s3_spend_records_insert ON s3_spend_records
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_records_update ON s3_spend_records;
CREATE POLICY s3_spend_records_update ON s3_spend_records
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_records_delete ON s3_spend_records;
CREATE POLICY s3_spend_records_delete ON s3_spend_records
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 302_spend_classifications.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic A · classifier output per spend line (separate table so
-- re-classification is versionable and analyst overrides are auditable).

CREATE TABLE IF NOT EXISTS s3_spend_classifications (
    classification_id   BIGSERIAL PRIMARY KEY,
    spend_record_id     BIGINT NOT NULL REFERENCES s3_spend_records (spend_record_id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id             UUID REFERENCES auth.users (id),   -- created_by metadata only
    scope3_category     SMALLINT CHECK (scope3_category BETWEEN 1 AND 15),
    eeio_sector_code    TEXT,
    eeio_sector_name    TEXT,
    ef_kg_co2e_per_usd  DOUBLE PRECISION,
    kg_co2e             DOUBLE PRECISION,
    confidence_score    DOUBLE PRECISION,
    data_source         TEXT NOT NULL DEFAULT 'spend',
    is_override         BOOLEAN NOT NULL DEFAULT false,
    flag_status         TEXT NOT NULL DEFAULT 'ok',
    ef_source           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_spend_classifications_org ON s3_spend_classifications (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_spend_classifications_record ON s3_spend_classifications (spend_record_id);

ALTER TABLE s3_spend_classifications ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_spend_classifications_select ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_select ON s3_spend_classifications
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_classifications_insert ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_insert ON s3_spend_classifications
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_classifications_update ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_update ON s3_spend_classifications
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_spend_classifications_delete ON s3_spend_classifications;
CREATE POLICY s3_spend_classifications_delete ON s3_spend_classifications
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 303_inventory_category_results.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic A · per-category rollup for an inventory version. Cat 1 may be
-- sourced from the product-PCF rollup (method='product_rollup') instead of
-- spend, recorded in `method` so provenance is explicit and there is no
-- double-count.

CREATE TABLE IF NOT EXISTS s3_inventory_category_results (
    result_id        BIGSERIAL PRIMARY KEY,
    inventory_id     BIGINT NOT NULL REFERENCES s3_inventory_versions (inventory_id) ON DELETE CASCADE,
    org_id           UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    scope3_category  SMALLINT NOT NULL CHECK (scope3_category BETWEEN 1 AND 15),
    method           TEXT NOT NULL DEFAULT 'spend'
                     CHECK (method IN ('spend', 'product_rollup', 'activity')),
    total_kg_co2e    DOUBLE PRECISION NOT NULL DEFAULT 0,
    line_count       INTEGER NOT NULL DEFAULT 0,
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (inventory_id, scope3_category)
);

CREATE INDEX IF NOT EXISTS idx_s3_inventory_category_results_org ON s3_inventory_category_results (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_inventory_category_results_inventory ON s3_inventory_category_results (inventory_id);

ALTER TABLE s3_inventory_category_results ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_inventory_category_results_select ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_select ON s3_inventory_category_results
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_category_results_insert ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_insert ON s3_inventory_category_results
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_category_results_update ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_update ON s3_inventory_category_results
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_inventory_category_results_delete ON s3_inventory_category_results;
CREATE POLICY s3_inventory_category_results_delete ON s3_inventory_category_results
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 304_questionnaire_requests.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic B · inbound questionnaire requests (a customer/retailer/CDP/
-- EcoVadis questionnaire to answer). Band 050-059. org_id RLS via is_org_member.

CREATE TABLE IF NOT EXISTS s3_questionnaire_requests (
    request_id      BIGSERIAL PRIMARY KEY,
    org_id          UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id         UUID REFERENCES auth.users (id),   -- created_by metadata only
    customer_name   TEXT,
    framework       TEXT NOT NULL DEFAULT 'generic'
                    CHECK (framework IN ('cdp', 'ecovadis', 'walmart', 'tesco_cdf', 'generic')),
    source_file     TEXT,
    deadline        DATE,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'in_progress', 'submitted', 'declined')),
    inventory_id    BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_questionnaire_requests_org ON s3_questionnaire_requests (org_id);

ALTER TABLE s3_questionnaire_requests ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_questionnaire_requests_select ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_select ON s3_questionnaire_requests
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_requests_insert ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_insert ON s3_questionnaire_requests
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_requests_update ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_update ON s3_questionnaire_requests
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_requests_delete ON s3_questionnaire_requests;
CREATE POLICY s3_questionnaire_requests_delete ON s3_questionnaire_requests
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 305_questionnaire_questions.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic B · parsed questions for a questionnaire request.

CREATE TABLE IF NOT EXISTS s3_questionnaire_questions (
    question_id          BIGSERIAL PRIMARY KEY,
    request_id           BIGINT NOT NULL REFERENCES s3_questionnaire_requests (request_id) ON DELETE CASCADE,
    org_id               UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    question_index       INTEGER NOT NULL DEFAULT 0,
    section              TEXT,
    question_text        TEXT NOT NULL,
    question_type        TEXT NOT NULL DEFAULT 'narrative'
                         CHECK (question_type IN ('numeric', 'boolean', 'select', 'narrative')),
    framework_field_key  TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_questionnaire_questions_org ON s3_questionnaire_questions (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_questionnaire_questions_request ON s3_questionnaire_questions (request_id);

ALTER TABLE s3_questionnaire_questions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_questionnaire_questions_select ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_select ON s3_questionnaire_questions
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_questions_insert ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_insert ON s3_questionnaire_questions
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_questions_update ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_update ON s3_questionnaire_questions
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_questionnaire_questions_delete ON s3_questionnaire_questions;
CREATE POLICY s3_questionnaire_questions_delete ON s3_questionnaire_questions
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 306_question_datapoint_mappings.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic B · question -> inventory-datapoint mapping + drafted answer.
-- mapped_value is ALWAYS a looked-up inventory datapoint (never generated);
-- unmappable questions carry flag_status='needs_human' with a null value.

CREATE TABLE IF NOT EXISTS s3_question_datapoint_mappings (
    mapping_id        BIGSERIAL PRIMARY KEY,
    question_id       BIGINT NOT NULL REFERENCES s3_questionnaire_questions (question_id) ON DELETE CASCADE,
    org_id            UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    datapoint_ref     TEXT,
    mapped_value      DOUBLE PRECISION,
    answer_text       TEXT,
    confidence_score  DOUBLE PRECISION,
    method            TEXT NOT NULL DEFAULT 'unmapped'
                      CHECK (method IN ('inventory', 'library', 'unmapped')),
    citation          TEXT,
    flag_status       TEXT NOT NULL DEFAULT 'needs_human',
    is_override       BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_qd_mappings_org ON s3_question_datapoint_mappings (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_qd_mappings_question ON s3_question_datapoint_mappings (question_id);

ALTER TABLE s3_question_datapoint_mappings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_qd_mappings_select ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_select ON s3_question_datapoint_mappings
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_qd_mappings_insert ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_insert ON s3_question_datapoint_mappings
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_qd_mappings_update ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_update ON s3_question_datapoint_mappings
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_qd_mappings_delete ON s3_question_datapoint_mappings;
CREATE POLICY s3_qd_mappings_delete ON s3_question_datapoint_mappings
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 307_answer_library.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic B · reusable prior answers (the compounding moat). On submit,
-- answered questions are written here keyed by framework_field_key /
-- question_signature so the next questionnaire can reuse them.

CREATE TABLE IF NOT EXISTS s3_answer_library (
    answer_id            BIGSERIAL PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id              UUID REFERENCES auth.users (id),   -- created_by metadata only
    framework_field_key  TEXT,
    question_signature   TEXT,
    answer_text          TEXT NOT NULL,
    source_request_id    BIGINT REFERENCES s3_questionnaire_requests (request_id) ON DELETE SET NULL,
    last_used_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_answer_library_org ON s3_answer_library (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_answer_library_key ON s3_answer_library (org_id, framework_field_key);

ALTER TABLE s3_answer_library ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_answer_library_select ON s3_answer_library;
CREATE POLICY s3_answer_library_select ON s3_answer_library
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_answer_library_insert ON s3_answer_library;
CREATE POLICY s3_answer_library_insert ON s3_answer_library
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_answer_library_update ON s3_answer_library;
CREATE POLICY s3_answer_library_update ON s3_answer_library
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_answer_library_delete ON s3_answer_library;
CREATE POLICY s3_answer_library_delete ON s3_answer_library
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 308_company_profiles.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic C · persisted company profile that drives the obligation
-- engine (one per org). Band 050-059. org_id is the RLS key via
-- public.is_org_member(org_id); user_id is created_by metadata only.

CREATE TABLE IF NOT EXISTS s3_company_profiles (
    profile_id             BIGSERIAL PRIMARY KEY,
    org_id                 UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id                UUID REFERENCES auth.users (id),   -- created_by metadata only
    annual_revenue_usd     DOUBLE PRECISION,
    employee_count         INTEGER,
    is_us_entity           BOOLEAN NOT NULL DEFAULT false,
    does_business_in_ca    BOOLEAN NOT NULL DEFAULT false,
    eu_turnover_eur        DOUBLE PRECISION,
    eu_subsidiary          BOOLEAN NOT NULL DEFAULT false,
    eu_branch_turnover_eur DOUBLE PRECISION,
    listed_jurisdictions   JSONB NOT NULL DEFAULT '[]'::jsonb,
    sector                 TEXT,
    is_flag_sector         BOOLEAN NOT NULL DEFAULT false,
    key_customers          JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (org_id)
);

CREATE INDEX IF NOT EXISTS idx_s3_company_profiles_org ON s3_company_profiles (org_id);

ALTER TABLE s3_company_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_company_profiles_select ON s3_company_profiles;
CREATE POLICY s3_company_profiles_select ON s3_company_profiles
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_company_profiles_insert ON s3_company_profiles;
CREATE POLICY s3_company_profiles_insert ON s3_company_profiles
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_company_profiles_update ON s3_company_profiles;
CREATE POLICY s3_company_profiles_update ON s3_company_profiles
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_company_profiles_delete ON s3_company_profiles;
CREATE POLICY s3_company_profiles_delete ON s3_company_profiles
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 309_obligations.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic C · evaluated obligations per org (snapshot of an engine run).
-- The ruleset itself is versioned DATA in the s3_obligations package, not a
-- table; this stores the OUTPUT of evaluating a profile against it.

CREATE TABLE IF NOT EXISTS s3_obligations (
    obligation_id     BIGSERIAL PRIMARY KEY,
    org_id            UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id           UUID REFERENCES auth.users (id),   -- created_by metadata only
    rule_id           TEXT NOT NULL,
    framework         TEXT NOT NULL,
    applies           TEXT NOT NULL CHECK (applies IN ('yes', 'uncertain', 'no')),
    reason            TEXT,
    threshold_detail  TEXT,
    confidence        TEXT,
    status            TEXT,
    due               JSONB NOT NULL DEFAULT '[]'::jsonb,
    assurance         TEXT,
    citation          TEXT,
    priority          INTEGER NOT NULL DEFAULT 0,
    ruleset_version   TEXT NOT NULL,
    evaluated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_obligations_org ON s3_obligations (org_id);

ALTER TABLE s3_obligations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_obligations_select ON s3_obligations;
CREATE POLICY s3_obligations_select ON s3_obligations
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_obligations_insert ON s3_obligations;
CREATE POLICY s3_obligations_insert ON s3_obligations
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_obligations_update ON s3_obligations;
CREATE POLICY s3_obligations_update ON s3_obligations
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_obligations_delete ON s3_obligations;
CREATE POLICY s3_obligations_delete ON s3_obligations
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 310_targets.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic D · SBTi targets. Band 310+ (Scope 3's second reserved block,
-- after 050-059). org_id RLS via public.is_org_member(org_id); user_id metadata.

CREATE TABLE IF NOT EXISTS s3_targets (
    target_id           BIGSERIAL PRIMARY KEY,
    org_id              UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id             UUID REFERENCES auth.users (id),   -- created_by metadata only
    type                TEXT NOT NULL DEFAULT 'near_term'
                        CHECK (type IN ('near_term', 'net_zero')),
    method              TEXT NOT NULL DEFAULT 'absolute'
                        CHECK (method IN ('absolute', 'intensity')),
    sbti_version        TEXT NOT NULL DEFAULT 'v2.0',
    base_year           INTEGER,
    target_year         INTEGER,
    reduction_pct       DOUBLE PRECISION,
    inventory_base_id   BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    status              TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'ready', 'validated')),
    assurance_required  BOOLEAN NOT NULL DEFAULT false,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_targets_org ON s3_targets (org_id);

ALTER TABLE s3_targets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_targets_select ON s3_targets;
CREATE POLICY s3_targets_select ON s3_targets
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_targets_insert ON s3_targets;
CREATE POLICY s3_targets_insert ON s3_targets
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_targets_update ON s3_targets;
CREATE POLICY s3_targets_update ON s3_targets
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_targets_delete ON s3_targets;
CREATE POLICY s3_targets_delete ON s3_targets
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 311_target_categories.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic D · per-category coverage for a target (V2.0 needs every
-- category >=5% of Scope 3 covered).

CREATE TABLE IF NOT EXISTS s3_target_categories (
    id                 BIGSERIAL PRIMARY KEY,
    target_id          BIGINT NOT NULL REFERENCES s3_targets (target_id) ON DELETE CASCADE,
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    category_num       SMALLINT NOT NULL CHECK (category_num BETWEEN 1 AND 15),
    pct_of_scope3      DOUBLE PRECISION,
    requires_coverage  BOOLEAN NOT NULL DEFAULT false,
    is_covered         BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (target_id, category_num)
);

CREATE INDEX IF NOT EXISTS idx_s3_target_categories_org ON s3_target_categories (org_id);
CREATE INDEX IF NOT EXISTS idx_s3_target_categories_target ON s3_target_categories (target_id);

ALTER TABLE s3_target_categories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_target_categories_select ON s3_target_categories;
CREATE POLICY s3_target_categories_select ON s3_target_categories
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_categories_insert ON s3_target_categories;
CREATE POLICY s3_target_categories_insert ON s3_target_categories
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_categories_update ON s3_target_categories;
CREATE POLICY s3_target_categories_update ON s3_target_categories
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_categories_delete ON s3_target_categories;
CREATE POLICY s3_target_categories_delete ON s3_target_categories
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 312_flag_targets.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic D · FLAG (Forest, Land & Agriculture) target attached to a
-- target when the company is FLAG-designated or FLAG >=20% of total.

CREATE TABLE IF NOT EXISTS s3_flag_targets (
    id                              BIGSERIAL PRIMARY KEY,
    target_id                       BIGINT NOT NULL REFERENCES s3_targets (target_id) ON DELETE CASCADE,
    org_id                          UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    flag_share_pct                  DOUBLE PRECISION,
    flag_target_type                TEXT,
    no_deforestation_commitment_date DATE,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (target_id)
);

CREATE INDEX IF NOT EXISTS idx_s3_flag_targets_org ON s3_flag_targets (org_id);

ALTER TABLE s3_flag_targets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_flag_targets_select ON s3_flag_targets;
CREATE POLICY s3_flag_targets_select ON s3_flag_targets
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_flag_targets_insert ON s3_flag_targets;
CREATE POLICY s3_flag_targets_insert ON s3_flag_targets
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_flag_targets_update ON s3_flag_targets;
CREATE POLICY s3_flag_targets_update ON s3_flag_targets
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_flag_targets_delete ON s3_flag_targets;
CREATE POLICY s3_flag_targets_delete ON s3_flag_targets
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 313_target_progress.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic E · progress snapshots (like-for-like real reduction vs a
-- target trajectory). Band 310+. org_id RLS via public.is_org_member(org_id).

CREATE TABLE IF NOT EXISTS s3_target_progress (
    progress_id           BIGSERIAL PRIMARY KEY,
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id               UUID REFERENCES auth.users (id),   -- created_by metadata only
    target_id             BIGINT REFERENCES s3_targets (target_id) ON DELETE SET NULL,
    base_inventory_id     BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    current_inventory_id  BIGINT REFERENCES s3_inventory_versions (inventory_id) ON DELETE SET NULL,
    current_year          INTEGER,
    actual_total_kg       DOUBLE PRECISION,
    real_total_kg         DOUBLE PRECISION,
    method_delta_kg       DOUBLE PRECISION,
    on_track              BOOLEAN,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_target_progress_org ON s3_target_progress (org_id);

ALTER TABLE s3_target_progress ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_target_progress_select ON s3_target_progress;
CREATE POLICY s3_target_progress_select ON s3_target_progress
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_progress_insert ON s3_target_progress;
CREATE POLICY s3_target_progress_insert ON s3_target_progress
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_progress_update ON s3_target_progress;
CREATE POLICY s3_target_progress_update ON s3_target_progress
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_target_progress_delete ON s3_target_progress;
CREATE POLICY s3_target_progress_delete ON s3_target_progress
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 314_base_year_recalcs.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic E · recorded base-year recalculation decisions (GHG Protocol
-- significance-threshold policy).

CREATE TABLE IF NOT EXISTS s3_base_year_recalcs (
    recalc_id        BIGSERIAL PRIMARY KEY,
    org_id           UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id          UUID REFERENCES auth.users (id),   -- created_by metadata only
    trigger          TEXT NOT NULL,
    significance_pct DOUBLE PRECISION,
    threshold_pct    DOUBLE PRECISION,
    recalc_required  BOOLEAN NOT NULL DEFAULT false,
    rationale        TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_base_year_recalcs_org ON s3_base_year_recalcs (org_id);

ALTER TABLE s3_base_year_recalcs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_base_year_recalcs_select ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_select ON s3_base_year_recalcs
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_base_year_recalcs_insert ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_insert ON s3_base_year_recalcs
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_base_year_recalcs_update ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_update ON s3_base_year_recalcs
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_base_year_recalcs_delete ON s3_base_year_recalcs;
CREATE POLICY s3_base_year_recalcs_delete ON s3_base_year_recalcs
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 315_suppliers.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic F · suppliers for cohorting + program scorecards. Band 310+.

CREATE TABLE IF NOT EXISTS s3_suppliers (
    supplier_id          BIGSERIAL PRIMARY KEY,
    org_id               UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id              UUID REFERENCES auth.users (id),   -- created_by metadata only
    name                 TEXT NOT NULL,
    scope3_category      SMALLINT NOT NULL CHECK (scope3_category BETWEEN 1 AND 15),
    emissions_kg         DOUBLE PRECISION NOT NULL DEFAULT 0,
    spend_usd            DOUBLE PRECISION NOT NULL DEFAULT 0,
    pcf_received         BOOLEAN NOT NULL DEFAULT false,
    dq_score             DOUBLE PRECISION,
    supplier_sbt_status  TEXT NOT NULL DEFAULT 'none'
                         CHECK (supplier_sbt_status IN ('none', 'committed', 'validated')),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_suppliers_org ON s3_suppliers (org_id);

ALTER TABLE s3_suppliers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_suppliers_select ON s3_suppliers;
CREATE POLICY s3_suppliers_select ON s3_suppliers
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_suppliers_insert ON s3_suppliers;
CREATE POLICY s3_suppliers_insert ON s3_suppliers
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_suppliers_update ON s3_suppliers;
CREATE POLICY s3_suppliers_update ON s3_suppliers
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_suppliers_delete ON s3_suppliers;
CREATE POLICY s3_suppliers_delete ON s3_suppliers
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 316_use_phase_specs.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic H · captured per-SKU use-phase specs (energy/water + use
-- profile) for Category 11 calculation. Band 310+.

CREATE TABLE IF NOT EXISTS s3_use_phase_specs (
    spec_id            BIGSERIAL PRIMARY KEY,
    org_id             UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id            UUID REFERENCES auth.users (id),   -- created_by metadata only
    product_ref        TEXT NOT NULL,
    energy_per_use_kwh DOUBLE PRECISION NOT NULL DEFAULT 0,
    water_l_per_use    DOUBLE PRECISION NOT NULL DEFAULT 0,
    standby_power_w    DOUBLE PRECISION NOT NULL DEFAULT 0,
    fuel_kwh_per_use   DOUBLE PRECISION NOT NULL DEFAULT 0,
    spec_source        TEXT,
    uses_per_year      DOUBLE PRECISION NOT NULL DEFAULT 0,
    lifetime_years     DOUBLE PRECISION NOT NULL DEFAULT 0,
    sub_sector         TEXT,
    units_sold         DOUBLE PRECISION NOT NULL DEFAULT 0,
    region             TEXT,
    mode               TEXT NOT NULL DEFAULT 'direct' CHECK (mode IN ('direct', 'indirect')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_use_phase_specs_org ON s3_use_phase_specs (org_id);

ALTER TABLE s3_use_phase_specs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_use_phase_specs_select ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_select ON s3_use_phase_specs
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_use_phase_specs_insert ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_insert ON s3_use_phase_specs
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_use_phase_specs_update ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_update ON s3_use_phase_specs
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_use_phase_specs_delete ON s3_use_phase_specs;
CREATE POLICY s3_use_phase_specs_delete ON s3_use_phase_specs
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

-- ----------------------------------------------------------
-- 317_claims.sql
-- ----------------------------------------------------------
-- Scope 3 · Epic I · recorded green-claim assessments (substantiation + dated
-- compliance flags). Levers + MAC are stateless compute; only claims persist.

CREATE TABLE IF NOT EXISTS s3_claims (
    claim_id              BIGSERIAL PRIMARY KEY,
    org_id                UUID NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id               UUID REFERENCES auth.users (id),   -- created_by metadata only
    claim_text            TEXT NOT NULL,
    jurisdiction          TEXT NOT NULL,
    substantiable         BOOLEAN NOT NULL DEFAULT false,
    substantiation_reason TEXT,
    ruleset_version       TEXT NOT NULL,
    flags                 JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s3_claims_org ON s3_claims (org_id);

ALTER TABLE s3_claims ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS s3_claims_select ON s3_claims;
CREATE POLICY s3_claims_select ON s3_claims
    FOR SELECT TO authenticated
    USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_claims_insert ON s3_claims;
CREATE POLICY s3_claims_insert ON s3_claims
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_claims_update ON s3_claims;
CREATE POLICY s3_claims_update ON s3_claims
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s3_claims_delete ON s3_claims;
CREATE POLICY s3_claims_delete ON s3_claims
    FOR DELETE TO authenticated
    USING (public.is_org_member(org_id));

COMMIT;
