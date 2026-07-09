-- Scope 2 ("Grid") — target-setting: SBTi-style reduction trajectories (range 040-049).
--
-- Org-level base-year total + future target (amount or % reduction).
-- Immutable base/target totals; mutable status/notes. Exactly one of
-- (target_amount_tco2e, target_pct_reduction) must be set.
--
-- APPLY TO A SUPABASE BRANCH DB FIRST (CLAUDE.md rule).

CREATE TABLE IF NOT EXISTS s2_targets (
    target_id               BIGSERIAL PRIMARY KEY,
    org_id                  UUID NOT NULL,
    base_year               INTEGER NOT NULL,
    base_year_tco2e         DOUBLE PRECISION NOT NULL,
    target_year             INTEGER NOT NULL,
    target_amount_tco2e     DOUBLE PRECISION,
    target_pct_reduction    DOUBLE PRECISION,
    trajectory_type         TEXT NOT NULL DEFAULT 'linear'
        CHECK (trajectory_type IN ('linear', 'exponential')),
    status                  TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'superseded', 'achieved')),
    notes                   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT exactly_one_target_method
        CHECK (
            (target_amount_tco2e IS NOT NULL AND target_pct_reduction IS NULL)
            OR (target_amount_tco2e IS NULL AND target_pct_reduction IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_s2_targets_org ON s2_targets (org_id);
CREATE INDEX IF NOT EXISTS idx_s2_targets_org_status ON s2_targets (org_id, status);

ALTER TABLE s2_targets ENABLE ROW LEVEL SECURITY;

-- RLS via is_org_member (standard Platform pattern).
DROP POLICY IF EXISTS s2_targets_select_org ON s2_targets;
CREATE POLICY s2_targets_select_org ON s2_targets
    FOR SELECT TO authenticated USING (public.is_org_member(org_id));

DROP POLICY IF EXISTS s2_targets_insert_org ON s2_targets;
CREATE POLICY s2_targets_insert_org ON s2_targets
    FOR INSERT TO authenticated
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s2_targets_update_org ON s2_targets;
CREATE POLICY s2_targets_update_org ON s2_targets
    FOR UPDATE TO authenticated
    USING (public.is_org_member(org_id))
    WITH CHECK (public.is_org_member(org_id));

DROP POLICY IF EXISTS s2_targets_delete_org ON s2_targets;
CREATE POLICY s2_targets_delete_org ON s2_targets
    FOR DELETE TO authenticated USING (public.is_org_member(org_id));
