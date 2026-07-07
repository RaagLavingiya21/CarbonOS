-- Scope 2 ("Grid") — utility accounts + bills (PRD 5.1). Migration range 040-049.
--
-- ISOLATION: intra-module FKs only (s2_sites). No FK to any Carbon OS table.
-- IMMUTABILITY (PRD 5.6): consumption on s2_utility_bills is never overwritten. A
-- correction or actual/true-up read INSERTs a new row and sets superseded_by_bill_id
-- on the old one; the calc engine ignores superseded rows. Enforced in the store layer.
--
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

CREATE TABLE IF NOT EXISTS s2_utility_accounts (
    account_id      BIGSERIAL PRIMARY KEY,
    site_id         BIGINT NOT NULL REFERENCES s2_sites(site_id) ON DELETE CASCADE,
    org_id          UUID NOT NULL,
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    utility_name    TEXT,
    account_number  TEXT,
    service_address TEXT,
    energy_carrier  TEXT NOT NULL DEFAULT 'electricity'
        CHECK (energy_carrier IN ('electricity','natural_gas','steam','heat','cooling')),
    source_type     TEXT NOT NULL DEFAULT 'manual'
        CHECK (source_type IN ('aggregator','csv','pdf','manual')),
    tariff_code     TEXT,
    active          BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS s2_utility_bills (
    bill_id               BIGSERIAL PRIMARY KEY,
    account_id            BIGINT NOT NULL REFERENCES s2_utility_accounts(account_id) ON DELETE CASCADE,
    org_id                UUID NOT NULL,
    user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    period_start          DATE NOT NULL,
    period_end            DATE NOT NULL,
    raw_quantity          DOUBLE PRECISION,
    raw_unit              TEXT,
    canonical_mwh         DOUBLE PRECISION,
    cost_usd              DOUBLE PRECISION,
    is_estimated_read     BOOLEAN NOT NULL DEFAULT false,
    is_cost_only          BOOLEAN NOT NULL DEFAULT false,
    conversion_note       TEXT,
    ingestion_method      TEXT,  -- aggregator | csv | pdf_ocr | manual
    source_ref            TEXT,  -- doc/file id or aggregator record id
    confidence            DOUBLE PRECISION,
    superseded_by_bill_id BIGINT REFERENCES s2_utility_bills(bill_id) ON DELETE SET NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_s2_accounts_site ON s2_utility_accounts (site_id);
CREATE INDEX IF NOT EXISTS idx_s2_accounts_org ON s2_utility_accounts (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_bills_account ON s2_utility_bills (account_id);
CREATE INDEX IF NOT EXISTS idx_s2_bills_org ON s2_utility_bills (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_bills_period ON s2_utility_bills (period_start, period_end);

ALTER TABLE s2_utility_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE s2_utility_bills ENABLE ROW LEVEL SECURITY;

-- Org-collaborative read/write; insert as the acting user.
-- Idempotent (safe to re-run): DROP POLICY IF EXISTS precedes each CREATE POLICY.
DROP POLICY IF EXISTS s2_accounts_select_org ON s2_utility_accounts;
CREATE POLICY s2_accounts_select_org ON s2_utility_accounts
    FOR SELECT TO authenticated USING (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_accounts_insert_self ON s2_utility_accounts;
CREATE POLICY s2_accounts_insert_self ON s2_utility_accounts
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
DROP POLICY IF EXISTS s2_accounts_update_org ON s2_utility_accounts;
CREATE POLICY s2_accounts_update_org ON s2_utility_accounts
    FOR UPDATE TO authenticated USING (public.shares_org_with(user_id))
    WITH CHECK (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_accounts_delete_org ON s2_utility_accounts;
CREATE POLICY s2_accounts_delete_org ON s2_utility_accounts
    FOR DELETE TO authenticated USING (public.shares_org_with(user_id));

DROP POLICY IF EXISTS s2_bills_select_org ON s2_utility_bills;
CREATE POLICY s2_bills_select_org ON s2_utility_bills
    FOR SELECT TO authenticated USING (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_bills_insert_self ON s2_utility_bills;
CREATE POLICY s2_bills_insert_self ON s2_utility_bills
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
-- UPDATE limited to metadata (e.g. setting superseded_by_bill_id); consumption
-- immutability is enforced in the store layer, not by column-level policy.
DROP POLICY IF EXISTS s2_bills_update_org ON s2_utility_bills;
CREATE POLICY s2_bills_update_org ON s2_utility_bills
    FOR UPDATE TO authenticated USING (public.shares_org_with(user_id))
    WITH CHECK (public.shares_org_with(user_id));
DROP POLICY IF EXISTS s2_bills_delete_org ON s2_utility_bills;
CREATE POLICY s2_bills_delete_org ON s2_utility_bills
    FOR DELETE TO authenticated USING (public.shares_org_with(user_id));
