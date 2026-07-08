# Scope 1 — Working Status / Resume-Here
Living doc. Design lives in the implementation plan (`~/.claude/plans/lucky-growing-planet.md`) + research (`~/Downloads/Scope1Research/`). This is current position + gotchas.
_Last updated: 2026-07-07 · Branch: feature/scope1-v2 (off main, 7 commits)_

## 0. Latest (commit c91a0f2) — V2 Priority 2 COMPLETE + security hardening
Wired the Bayou credential-connect routes and **fixed 3 real problems in the inherited migration 115 / store** (it was unapplied to prod, so fixed cheaply):
- **🔴 Key was readable by any org member.** The old RLS `SELECT ... USING (is_org_member(org_id))` exposed the raw `bayou_api_key` to any member via the anon key — contradicting "never exposed to frontend". Table is now **backend/service-role ONLY**: RLS enabled with **no anon/authenticated policies** (deny-by-default); the backend reads/writes via `get_service_client()` (bypasses RLS). Key never leaves the server; status DTOs never include it.
- **🔴 Missing INSERT policy** → `get_or_create_credentials` would have failed on the real DB (mocked tests hid it). Moot now (service-role bypasses RLS).
- **🔴 Destructive `DROP TABLE`** in the migration (would wipe credentials on re-run) — removed; now idempotent like the rest.
- Routes (`/api/scope1/bayou-credentials` GET status / POST set-key[admin] / DELETE disconnect[admin] / POST /sync[editor, PDF fetch mocked]). Frontend: admin-only "Bayou auto-connect" card on `/scope-1/settings`. **594 tests** (9 new). **Migration 115 (revised) still NOT applied to any DB.**


## 0b. V2 brief reconciliation + blockers (read at merge)
The V2 brief was re-issued; here's how each priority maps to what's actually built, and the two places the brief's assumptions don't match the code:

- **P2 auto-pull — DONE (commit 2068a00).** `/bayou-credentials/sync` now uses the org's stored key to `list_bills()` → map parsed bills → ingest into the OCR review queue (deduped, latest inventory), trusted Tier-2. Reviewer assigns source → calc via the existing path. 3 integration tests inject the client transport to mock Bayou's `/bills`. **Note:** Bayou's API is REST v2 (Basic auth, API key as user), **not GraphQL** as the brief says — the existing REST client is correct/verified. **Follow-ups:** real background poller (cron/worker) + auto-source-mapping so trusted bills skip manual review.

- **🚩 P1 blocker — IEA / Green-e / eGRID are Scope 2, not Scope 1.** The brief asks to seed "IEA defaults + Green-e residual mix" (and eGRID). Those are **purchased-electricity** emission factors = **Scope 2**. Scope 1 is direct combustion only; seeding electricity factors here would be a scope error / cross-module leakage. **Decision (kept from the prior session): deferred to Scope 2 integration — do NOT add them to `s1_factors`.** What P1 *did* deliver is real, correct: expanded EPA EF Hub combustion factors (14 fuels) with 40 CFR Part 98 citations + 4 seed-verification tests. Vintage: labeled "2025"; if a real "EF Hub 2026" table is published, values update via re-seed or the per-org EF-override feature (migration 110) — no code change needed.

- **🚩 P3 note — no `s1_facility.combustion_type` enum exists.** The brief says "extend the `s1_facility.combustion_type` enum," but the schema has no such column/enum: source breadth lives in the `s1_factors` EF library (fuels) + the free `source_category` on `s1_emission_source` (no CHECK constraint). Priority 3's substance (more combustion fuels) is done via the library (5ca106c); there is no enum to extend. If facility-level `combustion_type` is desired later it'd be a new migration in band 110–199, but it would duplicate the source model — flagging rather than adding speculatively.

## 1. Where we are
The Scope 1 (direct combustion emissions) MVP module is **merged to `main` via PR #24** and runs end-to-end against the shared Supabase dev DB. The defensible core is complete: org/entity/facility model → standards-correct per-gas engine → intake (manual/CSV/OCR/Bayou-PDF) → orchestration/readiness → GHG-Protocol/SB-253 reporting (+ PDF/XLSX) → audit/evidence → users & roles. Ships **dark** behind `NEXT_PUBLIC_SCOPE1_ENABLED`. Roadmap-wise we're ~85% through the MVP atomic-action list + now **V2 is underway** on `feature/scope1-v2` (7 commits complete).

## 2. V2 Work Complete (4 commits on feature/scope1-v2)
### Commit 5ca106c: V2 Priority 3 — Expanded combustion-source categories
- Extended EPA factors to include **residual fuel oils (#4, #5, #6)**, **lignite coal**, **wood + agricultural residue (biogenic CO2 segregation)**
- All factors from 40 CFR Part 98 Tables C-1/C-2 with proper HHV defaults and CH4/N2O per category
- 10 new tests verify each source calculates correctly end-to-end + citations present
- **Test count: 567 → 577 (+10)**

### Commit 17bfcaa: V2 Priority 2 — Bayou credential-connect auth handshake
- **Migration 115**: `s1_bayou_credentials` table (org-level, UNIQUE per org)
  - RLS via `is_org_member` (org-member-only read/write)
  - `bayou_api_key` encrypted at-rest by Supabase
  - Sync scheduling: `last_sync`, `next_sync`, `sync_interval` (1-hour default)
- **Data layer** (`db/s1_bayou_store.py`):
  - `get_or_create_credentials`: creates inactive row on first access
  - `set_api_key`: stores + activates (org-admin via RLS)
  - `get_active_api_key`: retrieves key for backend (never frontend)
  - `mark_sync_complete`: updates timestamps for scheduling
  - `should_sync`: checks readiness for background poll
- **API schemas** (SetBayouApiKeyRequest, BayouCredentialsResponse)
- 10 new tests verify credential lifecycle + sync scheduling
- **Test count: 577 → 587 (+10), but lint fix bumped to 581 after cleanup**
- Next: wire routes (GET/POST `/api/scope1/bayou-credentials`) + background sync (mocked for now)

### Commit 0a0f28a: V2 Priority 1 — Real reference data + seed verification
- 4 new tests verify `seed_s1_reference.py` will load correct factors:
  - All expanded sources present + cited
  - Biogenic flags correct
  - Sufficient stationary factors (36+) with all gases
- Ensures seed script produces real EPA EF Hub 2025 data with audit provenance
- **Test count: 581 (+4)**

### Commit 1e9aabc: Hygiene — lint fixes
- Ruff: fixed import order + whitespace in test files
- All 581 tests still passing

## 3. V2 Scope (per brief)
**Priority 1 — Real factor data**: ✅ Extended EPA EF Hub 2025 with more combustion sources + verification tests. IEA defaults + Green-e residual mix are Scope 2 factors (electricity, not combustion); deferred to Scope 2 integration.

**Priority 2 — Bayou-PDF automation**: ✅ **COMPLETE** (c91a0f2 store/routes/hardening + 2068a00 auto-pull). Credential store + auth handshake + routes + connect UI + security-hardened + **auto-pull sync** (key → `list_bills` → map parsed → ingest to OCR queue, deduped). Remaining follow-up: a real background poller (cron/worker) to call sync on schedule + auto-source-mapping so trusted bills skip manual review. See §0b.

**Priority 3 — Breadth**: ✅ Extended combustion-source categories (natural gas, coal types, fuel oils all supported).

## 4. Current State of MVP + V2
**Data model**: 14 stationary fuels (up from 7) × 3 gases (CO2/CH4/N2O) + mobile, process, fugitive, biogenic tracking.

**Tests**: 594 passing (target: >610 by end of V2). Next test opportunities:
- Bayou credential routes (POST/GET `/api/scope1/bayou-credentials`)
- Background sync scheduler + mocked Bayou bill fetch
- Intake integration (Bayou bill → extraction → record)
- E2E: set key → sync → ingest → calculate

**Migrations**: 110–114 now LIVE in prod (user applied). **115 (Bayou credentials, revised) still unapplied** — apply before V2 release.

## 5. Decisions + Why
**Biogenic CO2 for biomass**: marked in EPA factors (`wood`, `agricultural_residue` have `biogenic=True`), but calc engine requires explicit `biogenic=True` at intake time (app layer). Metadata for audit, behavior determined by intake layer (by design — allows orgs to declare fuels either way per their protocol).

**Residual oils as separate factors**: distinct CO2 values (#4: 75.15, #5: 75.12, #6: 75.10 kg/mmBtu), same CH4/N2O (petroleum category). Matches EPA Table C-1 granularity.

**Migration band 115**: uses second band (110–199 reserved for S1 in 2026-07-07 grant). Preserves 030–039 capacity.

**Bayou credentials RLS** (revised c91a0f2): org-level, one org = one Bayou account. The table is **backend/service-role only** — RLS is on with **no anon/authenticated policies** (deny-by-default), so the secret is never client-readable. Management is admin-gated at the **app layer** (`require_admin`), and the backend touches the table via `get_service_client()`. (The earlier "admin-only via RLS / encrypted at-rest" claim was wrong: is_org_member RLS actually exposed the key to every member.)

## 6. Gotchas & Lessons (Same as before + New)
- **Ruff import order**: pytest, stdlib (datetime, unittest), third-party (db), local imports. Auto-fix with `ruff check --fix`.
- **Bayou credentials**: the `s1_bayou_credentials` table is **service-role only** (RLS deny-by-default) — the anon/user client can't read it, so the key can't leak to the frontend. Backend accesses it via `get_service_client()`. Never put `bayou_api_key` in an API response or log. (Disk "at-rest" encryption is NOT app-level protection — don't rely on it to hide the secret from members; the RLS design does that.)
- **Sync scheduling**: `next_sync` NULL means never synced (should_sync returns True). Timestamp comparison assumes ISO 8601 strings + UTC timezone.
- **Test mocking**: Bayou store tests use `unittest.mock.MagicMock` (no pytest-mock installed). Chain mocks for Supabase `.table().select().eq().limit().execute()`.

## 7. Next Steps (Post-V2)
- ~~Wire Bayou credential routes~~ ✅ done (c91a0f2). Remaining Bayou follow-up: **real background poller + real bill fetch→OCR→record** (sync endpoint is mocked today).
- **Apply migration 115 (revised)** to dev + prod (110–114 already live). Manual via Supabase SQL Editor / psycopg.
- **E2E V2 testing**: set Bayou key → verify active → schedule sync → mock bill fetch → ingest → calculate.
- **Target: 610+ tests by release** (currently 590; ~20 more from the real sync/ingest path + E2E).
- **Scope 1 V2 release**: feature/scope1-v2 → main (after Scope 2/3 integration tests pass).
- **Other open options** (not started): RLS-hard role enforcement, ESRS/CDP/GHGRP exports.

## 8. Files Modified (V2)
- `s1_factors/epa_library.py` — 14 fuels + biogenic flags
- `supabase/migrations/115_s1_bayou_credentials.sql` — credential table + RLS
- `db/s1_bayou_store.py` — credential data layer (new)
- `api/models/scope1_schemas.py` — Bayou request/response schemas (new)
- `tests/test_s1_expanded_combustion.py` — 10 tests (new)
- `tests/test_s1_bayou_credentials.py` — 10 tests (new)
- `tests/test_s1_seed_reference_data.py` — 4 tests (new)

