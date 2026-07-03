# Wave 2 Implementation Plan — "Close the Share Loop" (PACT exchange, thin slice)

**Executes:** Wave 2 of `PRODUCT_STRATEGY.md`. Read `PRODUCT_STRATEGY.md`, `PCF_PLATFORM_DESIGN.md`, and `CLAUDE.md` first.
**Branch:** `feature/wave-2-share` (created off `main`, which has Phases 1–4 + Wave 1 merged).
**Two workstreams:** S (Serve) then R (Receive) — reasonable as two sequential PRs. Commit each in small logical steps.

## Why
Today "Share" = the analyst downloads a PACT JSON file and emails it. The research's thesis is the **network**: serve footprints to customers, receive requests from them. This is the deliberate thin slice — tokenized public links, not full PACT OAuth/conformance. It pays off Wave 1: only **published** (reviewed, immutable) footprints are shareable.

## Instructions for the implementer
- Implement exactly what this plan says. If something is ambiguous or looks wrong, STOP and report — do not improvise.
- Commit in small steps. Test every migration on a local DB first. Never write credentials into source files.
- Recommended order: **S (Serve) first, then R (Receive)** — R's "fulfil" reuses S's share-creation.

## Locked decisions
1. **Serve = tokenized public share link** to a *published* footprint; recipient opens it with no login (read-only page + PACT JSON download); per-footprint, revocable.
2. **Receive = in-app request inbox via a public form** reached through an org's public link; the analyst fulfils by attaching a published footprint → a share link.
3. **Only `published` footprints are shareable/fulfillable.** Engine unchanged (spend-based). No OAuth, no PACT `/events`, no conformance.

## SECURITY is the primary constraint (first public-facing surface)
- All unauthenticated endpoints live under a single `/api/public/` prefix, added to the bypass in `api/middleware/auth.py` (`PUBLIC_PREFIXES`). **Nothing else bypasses auth.**
- Public reads use the **service-role client** (`db.client.get_service_client`, as `db/org_store.py` does) — the recipient has no JWT, so **the token IS the access control**: look up the share by token → verify **not revoked AND product `status == "published"`** → read exactly that one product + line items → build the view.
- **Never accept a raw `product_id` on a public endpoint** (no enumeration). Tokens are unguessable: `secrets.token_urlsafe(32)`.
- Public responses **must not leak** `user_id`, owner identity, other footprints, or internal ids beyond what the view needs.
- Known limitation to note in code comments (not built): no rate-limiting infra on the public POST — mitigate by length-capping/validating inputs.

## Do-NOT-touch
- `parsing/`, `factors/`, `calc/*`, and the Phase 1–4 + Wave 1 calc/lineage/PDS/DQR/provenance logic (call/read only — reuse `db.reader.get_footprint_provenance`, `exchange.pact.build_product_footprint`, `db.reader.get_product_by_id`)
- Existing migrations `001`–`025`; `app.py`, `pages/`, `.github/workflows/`
- The authenticated auth flow — only *add* the `/api/public/` bypass; do not weaken existing checks.

---

## Workstream S — Serve (shareable published footprint)

**S1. Migration `supabase/migrations/026_footprint_shares.sql`** — `footprint_shares`: `share_id BIGSERIAL PK`, `share_token TEXT UNIQUE NOT NULL`, `product_id BIGINT NOT NULL`, `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`, `recipient_label TEXT`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `revoked_at TIMESTAMPTZ`. Indexes on `share_token`, `product_id`, `user_id`. Enable **RLS** with owner policies (`user_id = auth.uid()`) for the authenticated side; public reads go through the service client (RLS bypassed) with the token+published check in code.

**S2. `db/share_store.py` (new)** —
- `create_share(product_id, *, recipient_label, user_id, access_token) -> dict`: verify the product is owned and `status == "published"` (else `ValueError`); `share_token = secrets.token_urlsafe(32)`; insert; audit-log via `db.copilot_store.append_audit_log`; return `{share_token, share_id}`.
- `get_shared_footprint(share_token) -> dict | None` (**service client**): find the share; return `None` if missing, revoked, or product not `published`; else assemble the read-only view reusing `get_footprint_provenance` (Wave 1) + `build_product_footprint` (PACT). **Strip `user_id` and any owner internals** from the returned dict.
- `list_shares_for_product(product_id, access_token)`; `revoke_share(share_id, *, user_id, access_token)` (set `revoked_at`; audit-log).

**S3. API** — authenticated (new router `api/routes/shares.py`, registered in `api/main.py`, or extend `analyzer.py`): `POST /api/analyses/{product_id}/shares` (409 if not published), `GET /api/analyses/{product_id}/shares`, `DELETE /api/shares/{share_id}`. **Public** (new router `api/routes/public.py`, registered): `GET /api/public/footprints/{share_token}` → read-only view or 404; `GET /api/public/footprints/{share_token}/pact` → PACT JSON or 404. Add `/api/public/` to `PUBLIC_PREFIXES` in `api/middleware/auth.py`. New Pydantic models in `api/models/schemas.py`.

**S4. Frontend** —
- Detail page `frontend/src/app/analyzer/[id]/page.tsx`: a **"Share"** action shown only when `status == "published"` → creates a link, shows it copyable (+ optional recipient label), lists active shares with **Revoke**.
- New **bare/public** route `frontend/src/app/shared/[token]/page.tsx`: add `/shared` handling to `bareRoutes` in `frontend/src/components/app-shell.tsx` (like `/demo` — no chrome, no auth redirect). Renders total, hotspots, DQR, provenance, and a "Download PACT JSON" button. Calls the public API with **no auth header**.
- `frontend/src/lib/api.ts`: share CRUD (authenticated) + a no-auth `fetchPublicFootprint(token)` / `fetchPublicPact(token)` helper (don't attach the Bearer token on these).

**S5. Tests** — `create_share` rejects a non-published product (ValueError → 409); `get_shared_footprint` returns the view for a valid token and `None` for revoked/unknown/unpublished; **the public view omits `user_id`**; public PACT still validates against `tests/fixtures/pact_v3_product_footprint_schema.json`; a public endpoint is reachable without a JWT (mirror the `tests/test_error_handling.py` client style with no auth header).

---

## Workstream R — Receive (PCF request inbox)

**R1. Migration `supabase/migrations/027_pcf_requests.sql`** — `pcf_requests`: `request_id BIGSERIAL PK`, `org_id UUID NOT NULL`, `requester_name TEXT`, `requester_email TEXT`, `requester_company TEXT`, `product_name TEXT`, `message TEXT`, `status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','fulfilled','declined'))`, `fulfilled_share_id BIGINT`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`. Indexes on `org_id`, `status`. RLS for the authenticated inbox (org members); public insert goes through the service client.

**R2. `db/request_store.py` (new)** —
- `create_request(org_id, *, requester_name, requester_email, requester_company, product_name, message) -> int` (**service client**, public path; length-cap all text inputs, e.g. ≤2000 chars).
- `list_requests_for_org(access_token, *, user_id)` (inbox; reuse `db.org_store.get_active_org_member_ids` for scoping).
- `fulfil_request(request_id, product_id, *, user_id, access_token)`: verify the footprint is published, create+attach a share (reuse `share_store.create_share`), set `status='fulfilled'`, `fulfilled_share_id`; audit-log. `decline_request(request_id, *, user_id, access_token)` → `status='declined'`.

**R3. API** — public in `api/routes/public.py`: `POST /api/public/pcf-requests` (body: `org_id`, requester fields, `product_name`, `message`) → creates a request. Authenticated (new `api/routes/requests.py` or extend): `GET /api/pcf-requests` (org inbox), `POST /api/pcf-requests/{id}/fulfil` (body: `product_id` of a published footprint → returns the new share link), `POST /api/pcf-requests/{id}/decline`.

**R4. Frontend** —
- New **bare/public** route `frontend/src/app/request/[orgId]/page.tsx`: a "Request a product carbon footprint" form (company, product, requester name/email, message) → `POST /api/public/pcf-requests` with `orgId` from the path; success confirmation. Add `/request` to `bareRoutes`.
- Authenticated **"Requests"** inbox `frontend/src/app/requests/page.tsx` + a sidebar + ⌘K nav entry (`app-shell.tsx` `navItems` and `CommandMenu.tsx` `NAV`, per the Wave-1/Phase-2 nav pattern): list open requests; each has **Fulfil** (pick a published footprint → generate+attach a share link, status→fulfilled, show the link) and **Decline**.
- Surface the org's public request link on `frontend/src/app/settings/org/page.tsx` ("Your PCF request link: …/request/{orgId}", copyable).

**R5. Tests** — `create_request` inserts an open request; `list_requests_for_org` is org-scoped; `fulfil_request` requires a published footprint, creates+links a share, sets fulfilled; `decline_request` sets declined; the public POST works without a JWT.

---

## Acceptance criteria (whole plan)
```bash
ruff check --ignore E501 evals tests calc parsing factors api llm copilot gap_analyzer rag db observability exchange
pytest tests -v
cd frontend && npm run lint && npm run build
```
Manual demo: publish a footprint → **Share** → open the token URL in a **logged-out** browser → read-only footprint + provenance + PACT JSON download → **Revoke** → same URL now 404s. Then: open the org's public **request** link logged-out → submit a PCF request → it appears in the analyst **Requests** inbox → **Fulfil** with a published footprint → a share link is generated and the request marks fulfilled.

## Out of scope (Wave 2)
Full PACT REST conformance / OAuth2 / `POST /events` webhooks; rate-limiting infra; requesting from your *own* suppliers via the network (still the email copilot); Wave 3 corporate roll-up; the hybrid activity engine.

## Review lens (post-implementation) — SECURITY FIRST
No unauthenticated read beyond a valid, non-revoked token to a *published* footprint; no `user_id`/owner leakage; no `product_id` accepted on public endpoints (no enumeration); `/api/public/` is the *only* auth exception and it's scoped exactly to these routes; public POST inputs are length-capped. Then the usual "mocks-pass-but-production-breaks" (service-client vs RLS mismatch, a column not selected, missing org scoping on the inbox).
