# Scope 1 — Working Status / Resume-Here
Living doc. Design lives in the implementation plan (`~/.claude/plans/lucky-growing-planet.md`) + research (`~/Downloads/Scope1Research/`). This is current position + gotchas.
_Last updated: 2026-07-07 · Branch: feature/scope1-v2 (off main, 4 commits)_

## 1. Where we are
The Scope 1 (direct combustion emissions) MVP module is **merged to `main` via PR #24** and runs end-to-end against the shared Supabase dev DB. The defensible core is complete: org/entity/facility model → standards-correct per-gas engine → intake (manual/CSV/OCR/Bayou-PDF) → orchestration/readiness → GHG-Protocol/SB-253 reporting (+ PDF/XLSX) → audit/evidence → users & roles. Ships **dark** behind `NEXT_PUBLIC_SCOPE1_ENABLED`. Roadmap-wise we're ~85% through the MVP atomic-action list + now **V2 is underway** on `feature/scope1-v2` (4 commits complete).

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

**Priority 2 — Bayou-PDF automation**: ✅ Auth handshake + credential store complete. Remaining: wire routes + background sync task (PDF fetch/OCR mocked per brief).

**Priority 3 — Breadth**: ✅ Extended combustion-source categories (natural gas, coal types, fuel oils all supported).

## 4. Current State of MVP + V2
**Data model**: 14 stationary fuels (up from 7) × 3 gases (CO2/CH4/N2O) + mobile, process, fugitive, biogenic tracking.

**Tests**: 581 passing (target: >610 by end of V2). Next test opportunities:
- Bayou credential routes (POST/GET `/api/scope1/bayou-credentials`)
- Background sync scheduler + mocked Bayou bill fetch
- Intake integration (Bayou bill → extraction → record)
- E2E: set key → sync → ingest → calculate

**Migrations unapplied**: 110–114 (EF overrides, trends, base-year recalc, fugitive, process), now **115 (Bayou credentials)**. Prod needs all 6 before V2 release.

## 5. Decisions + Why
**Biogenic CO2 for biomass**: marked in EPA factors (`wood`, `agricultural_residue` have `biogenic=True`), but calc engine requires explicit `biogenic=True` at intake time (app layer). Metadata for audit, behavior determined by intake layer (by design — allows orgs to declare fuels either way per their protocol).

**Residual oils as separate factors**: distinct CO2 values (#4: 75.15, #5: 75.12, #6: 75.10 kg/mmBtu), same CH4/N2O (petroleum category). Matches EPA Table C-1 granularity.

**Migration band 115**: uses second band (110–199 reserved for S1 in 2026-07-07 grant). Preserves 030–039 capacity.

**Bayou credentials RLS**: org-level, not per-user. One org = one Bayou account. Admin-only management (RLS enforced).

## 6. Gotchas & Lessons (Same as before + New)
- **Ruff import order**: pytest, stdlib (datetime, unittest), third-party (db), local imports. Auto-fix with `ruff check --fix`.
- **Bayou credentials**: encryption is at-rest only (Supabase DATABASE_URL encryption). Never expose `bayou_api_key` in API response or logs.
- **Sync scheduling**: `next_sync` NULL means never synced (should_sync returns True). Timestamp comparison assumes ISO 8601 strings + UTC timezone.
- **Test mocking**: Bayou store tests use `unittest.mock.MagicMock` (no pytest-mock installed). Chain mocks for Supabase `.table().select().eq().limit().execute()`.

## 7. Next Steps (Post-V2)
- **V2 completion**: Wire Bayou credential routes + background sync task (2–3 integration tests; mocked PDF fetch).
- **Apply migrations 110–115** to dev + prod DBs (manual via Supabase SQL Editor or psycopg).
- **E2E V2 testing**: set Bayou key → verify active → schedule sync → mock bill fetch → ingest → calculate.
- **Target: 610+ tests by release** (currently 581; need 29+ more from Bayou routes + E2E).
- **Scope 1 V2 release**: feature/scope1-v2 → main (after Scope 2/3 integration tests pass).

## 8. Files Modified (V2)
- `s1_factors/epa_library.py` — 14 fuels + biogenic flags
- `supabase/migrations/115_s1_bayou_credentials.sql` — credential table + RLS
- `db/s1_bayou_store.py` — credential data layer (new)
- `api/models/scope1_schemas.py` — Bayou request/response schemas (new)
- `tests/test_s1_expanded_combustion.py` — 10 tests (new)
- `tests/test_s1_bayou_credentials.py` — 10 tests (new)
- `tests/test_s1_seed_reference_data.py` — 4 tests (new)

