# UI/UX Upgrade & Onboarding Plan

**Author role:** Senior PM/design-eng perspective (Stripe / Watershed / Linear lineage)
**Branch:** `feature/ui-ux-upgrade`
**Status:** Planning — no code yet. Each step is sized for one focused session.

This plan has two tracks that ship in parallel-ish:
- **Track A — Design system & "feel":** make the product look and feel sharp, calm, and premium.
- **Track B — Onboarding & explainability:** make a cold visitor (e.g. a SaaS PM with no carbon background) instantly understand what this is, what problem it solves, and how to use it.

---

## 0. Current-State Audit (what we're fixing)

Grounded in the actual frontend (`frontend/src/`):

| Area | Today | Problem |
|------|-------|---------|
| Surfaces | `glass-card`, `backdrop-blur`, `bg-white/80`, radial gradients (`app-shell.tsx`, `auth-form.tsx`) | Dated glass-morphism; reads "template." Premium apps use flat surfaces + hairline borders. |
| Color | Emerald primary (`160 84% 28%`) applied broadly on gradients/chips/hovers | One loud accent everywhere = noisy. Premium = quiet, near-monochrome, accent used sparingly. |
| Type | Default font, ad-hoc `text-sm/base/xl`, `radius: 0.9rem` | No type scale, no tracking discipline. Type is the #1 lever for "feels designed." |
| Shadows | `shadow-soft` (big blurred), `shadow-md` on hover | Heavy/soft shadows read consumer, not enterprise. |
| Motion | Mostly `transition` defaults | No intentional easing/duration system; no micro-interactions. |
| Dark mode | `darkMode: ["class"]` configured, no tokens | Configured but unbuilt. Linear-tier products treat dark as first-class. |
| Entry point | `/login` is the front door | A cold visitor sees a login box, learns nothing about the product. |
| Dashboard | Chat hero + flat suggestion/module cards (`page.tsx`) | Functional but doesn't teach the "job" of each module. |
| Modules | Jump straight into the tool (`analyzer`, `gap-analysis`, etc.) | No consistent "what is this / why / how" framing per module. |
| Empty states | Minimal | Missed teaching moments; new users hit blank screens. |

---

## 1. Design North Star & Research Synthesis

We are not copying any one app — we're borrowing the *principles* that make each feel premium, and adapting to a **climate/enterprise-analyst** context (auditable, trustworthy, calm).

**What we take from each:**

- **Linear** — restraint. Near-monochrome palette, one accent, hairline borders, flat surfaces, tight heading tracking, fast purposeful motion (150–200ms), keyboard-first, dense-but-legible. The "expensive" feeling comes from *consistency and restraint*, not decoration.
- **Claude** — warmth + clarity. A touch of serif/editorial type for headings, generous reading measure, soft neutral background (not stark white), conversational tone, content-first layouts.
- **Watershed** (most relevant — same domain) — editorial calm for a serious subject. Lots of whitespace, deep ink/forest-green ink color, data presented with confidence and citations, trustworthy and quiet rather than flashy. Good model for "auditable & professional."
- **Slack** — clear information hierarchy, sidebar nav done well, excellent empty/onboarding states, friendly micro-copy, strong affordances for "what do I do next."

**The synthesized direction for this product:** *Quiet, editorial, trustworthy.* Flat surfaces, hairline borders, a calm neutral canvas, one deep-green ink as the brand anchor, a single restrained accent, real typography, and motion that's fast and purposeful. Every number traceable to a source (reinforces the product's core promise of auditability).

**Three design principles to enforce in review:**
1. **Restraint** — if an element doesn't earn its color/shadow/border, remove it.
2. **Hierarchy** — every screen has exactly one primary action and a clear primary/secondary/tertiary text ramp.
3. **Traceability as aesthetic** — citations, sources, and confidence are shown as first-class, well-styled UI (this *is* the brand).

---

## TRACK A — Design System & Feel

### A-1: Design token foundation (color, type, spacing, radius, shadow, motion)

**Goal:** Replace the current token set with a disciplined system. This is the single highest-leverage step — everything else inherits from it.

**Files:**
- `frontend/src/app/globals.css` — rewrite `:root` tokens; add a real `.dark` block
- `frontend/tailwind.config.ts` — extend type scale, tracking, shadow, motion timing, radius
- `frontend/src/app/layout.tsx` — wire fonts (next/font)

**Decisions to encode:**
- **Color:** Move from "emerald everywhere" to a **neutral canvas + deep-green ink + one accent**.
  - Canvas: warm off-white (e.g. `40 30% 98%`), not blue-gray.
  - Ink/foreground: deep forest/charcoal (e.g. `170 25% 12%`).
  - Brand primary: a more sophisticated deep green (e.g. `162 70% 22%`), used sparingly for primary actions only.
  - Add a **semantic data palette** for charts/badges: success/low-emission (green), warning/medium (amber), hotspot/high (a restrained red-orange), neutral (gray). Pin exact stops so hotspot visualizations are consistent and never rainbow.
  - Borders: hairline, low-contrast (`170 15% 90%` light / subtle white-alpha dark).
- **Typography:** Adopt `next/font`.
  - Headings: a tight display sans (Inter/Geist) tracked `-0.02em`, OR a subtle serif for editorial warmth (decide in A-1; recommend sans display for enterprise, serif optional for marketing pages).
  - Body: Inter/Geist, 15–16px, line-height 1.6.
  - **Numeric/tabular:** tabular figures for all emission numbers, money, percentages (critical for a data product — columns must align).
  - Define a strict scale: display / h1 / h2 / h3 / body-lg / body / small / caption. No ad-hoc sizes after this.
- **Radius:** Reduce from `0.9rem` to a tighter, more enterprise `0.5rem` (cards) with `0.375rem` controls. (Big radii read consumer.)
- **Shadow:** Replace `shadow-soft` with a 2-tier system: `shadow-xs` (hairline + 1px, for resting cards) and `shadow-overlay` (for popovers/drawers/command palette only). Kill blurred consumer shadows.
- **Motion:** Define tokens — `--ease-out: cubic-bezier(0.2, 0, 0, 1)`, durations `120ms` (micro), `200ms` (standard), `320ms` (panel). Apply consistently.
- **Remove** `.glass-card`, `backdrop-blur`, and radial-gradient backgrounds.

**Verify:** A single refactored card and button visibly change. Type scale renders. Dark mode toggles (even if pages aren't fully migrated yet). Document the tokens in a short `frontend/DESIGN.md`.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section A-1. Rewrite the design token foundation in frontend/src/app/globals.css and tailwind.config.ts. Replace the emerald-on-glass system with: a warm neutral off-white canvas, deep-green ink foreground, a restrained deep-green primary used sparingly, hairline low-contrast borders, and a pinned semantic data palette (low/medium/high-emission + neutral). Add real CSS variables for a full type scale and motion (ease + durations). Wire next/font in layout.tsx (display sans for headings tracked -0.02em, Inter/Geist body, tabular figures for numbers). Reduce radius to 0.5rem cards / 0.375rem controls. Add a proper .dark token block. Remove .glass-card, backdrop-blur, and radial-gradient backgrounds. Write frontend/DESIGN.md documenting every token and when to use it. Don't migrate all pages yet — just prove it on one card + button + the token file.
```

---

### A-2: Core primitive refresh (Button, Card, Input, Badge, Alert, Select, etc.)

**Goal:** Bring every shadcn primitive in `frontend/src/components/ui/` in line with the new tokens, with proper states.

**Files:** all of `frontend/src/components/ui/*`

**What "proper" means (the small details):**
- **Button:** crisp focus-visible ring (2px, offset), `active:` press state (subtle translate/scale), disabled with reduced opacity + `cursor-not-allowed`, loading variant with inline spinner, icon-button alignment fixed. Variants: primary / secondary / ghost / outline / destructive — all using new tokens.
- **Card:** flat surface, hairline border, `shadow-xs`, no blur. Hover elevation only where interactive.
- **Input/Textarea/Select:** consistent height (36/40px), hairline border, focus ring matches button, clear placeholder color (tertiary text), invalid state styling.
- **Badge:** map to the semantic data palette (confidence, flag status, emission tier). Text uses the dark stop of its own ramp (never black-on-color).
- **Alert:** success/warning/destructive/info, with icon, using semantic tokens.
- Add **Skeleton**, **Tooltip**, **Toast/Sonner**, and **Separator** primitives (missing today; needed for polish steps).

**Verify:** A `/styleguide` route (dev-only) renders every primitive in every state, light + dark. This becomes the visual regression reference.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section A-2. Refresh every primitive in frontend/src/components/ui/ to use the A-1 tokens, with complete states: focus-visible rings, active/press, disabled, loading, invalid. Fix icon-button alignment and control heights. Map Badge to the semantic data palette. Add missing primitives: Skeleton, Tooltip, Toast (sonner), Separator. Build a dev-only /styleguide page that renders every component in every state in both light and dark mode. Keep APIs backward-compatible so existing pages don't break.
```

---

### A-3: App shell, navigation & global chrome

**Goal:** Make the frame (sidebar, header, mobile nav) feel Linear-grade.

**Files:** `frontend/src/components/app-shell.tsx`, `WorkspaceBadge.tsx`, `GlobalChatIcon.tsx`

**Refinements:**
- Flat sidebar (no blur), hairline right border, refined active state (subtle filled pill + accent left-marker, not a flat accent block), proper icon weight consistency.
- Tighten the logo lockup; smaller, sharper brand mark.
- Header: remove blur, hairline bottom border, add a global **⌘K command menu** trigger (search/jump to module/start workflow) — this single feature reads "serious product."
- User/workspace block: cleaner, with avatar, role, and a dropdown (not a raw button).
- Mobile nav: replace the horizontal pill scroller with a clean bottom-sheet or refined top bar.
- Dark-mode toggle in the header.

**Verify:** Navigate every route; active states correct; ⌘K opens; dark toggle works; mobile layout clean at 375px.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section A-3. Refine app-shell.tsx and global chrome to a flat, hairline-bordered, Linear-grade frame. Improve the sidebar active state (filled pill + left accent marker), tighten the logo lockup, remove all backdrop-blur. Add a ⌘K command menu (jump to any module / start any workflow / search threads) and a dark-mode toggle in the header. Replace the mobile pill-scroller nav with a clean responsive pattern. Upgrade the workspace/user block to an avatar + dropdown.
```

---

### A-4: Data visualization & "auditable numbers" system

**Goal:** This is a carbon-accounting product — the way we render numbers, hotspots, breakdowns, confidence, and citations *is* the brand. Make it best-in-class.

**Files:** new `frontend/src/components/data/` (e.g. `MetricCard.tsx`, `HotspotBar.tsx`, `BreakdownTable.tsx`, `ConfidenceBadge.tsx`, `SourceCitation.tsx`); apply in `analyzer/`, `analyzer/[id]/`, panels.

**Specifics:**
- **MetricCard:** big tabular number, unit label (`kg CO₂e`), trend/context, source footnote. Consistent across the app.
- **HotspotBar / breakdown:** horizontal share bars using the pinned emission-tier palette; always sorted desc; the #1 hotspot visually distinct. Hover = exact value + source.
- **BreakdownTable:** tabular figures, right-aligned numbers, sticky header, flag/confidence chips inline, expandable rows for line-item detail + citation.
- **ConfidenceBadge:** low/med/high mapped to palette, with tooltip explaining the score.
- **SourceCitation:** a refined inline component (e.g. `Open CEDA 2025 · sector · country`) — small, monospace-ish, always present next to any factor. Reinforces auditability.
- Consider a lightweight chart lib only if needed (recharts/visx) — but bars/tables can be pure CSS and look better.

**Verify:** The analyzer results and saved-analysis pages render with the new data components; numbers align; every factor shows a citation; hotspots read instantly.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section A-4. Build a reusable data-display system in frontend/src/components/data/: MetricCard, HotspotBar, BreakdownTable, ConfidenceBadge, SourceCitation — all using tabular figures, right-aligned numbers, and the pinned emission-tier palette. Every emission factor must render a SourceCitation; every confidence must render a ConfidenceBadge with an explanatory tooltip. Apply these to the analyzer results view, analyzer/[id], and the BOM/Supplier panels. Hotspots always sorted descending with the top contributor visually distinct.
```

---

### A-5: Motion, micro-interactions, loading & empty/error states

**Goal:** The "1000 small details" pass.

**Scope (apply across the app):**
- **Loading:** replace spinners/blank screens with **skeletons** that match final layout (dashboard cards, thread list, results table, panels).
- **Streaming:** refine the chat typing indicator and token streaming feel (`ChatMessage.tsx`).
- **Transitions:** page/route transitions, panel open/close (the split-layout), tab switches, list item enter — all using A-1 motion tokens.
- **Micro-interactions:** button press, card hover lift, copy-to-clipboard confirmation, optimistic UI on send, toast on save/error.
- **Empty states:** every list/table/panel gets a designed empty state with an icon, one-line explanation, and a primary CTA (these double as onboarding — see Track B).
- **Error states:** in-context error cards with retry (not raw text), consistent with A-2 Alert.
- **Accessibility:** focus traps in drawers/modals, `prefers-reduced-motion` respected, keyboard nav through nav + command menu, ARIA on icon-only buttons.

**Verify:** Throttle the network — every async surface shows a skeleton, not a blank. Trigger errors — every one is a styled retto. Tab through the app with keyboard only.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section A-5. Do the polish pass: replace all loading spinners/blank screens with layout-matched skeletons; refine chat streaming + typing indicator; add consistent route/panel/tab/list motion using the A-1 tokens; add micro-interactions (press, hover lift, copy confirmation, optimistic send, toasts on save/error); design an empty state for every list/table/panel (icon + explanation + CTA); convert all error states to styled retry cards. Respect prefers-reduced-motion, add focus traps to drawers/modals, and ensure full keyboard navigation + ARIA on icon buttons.
```

---

## TRACK B — Onboarding & Explainability

> Goal: a cold visitor (SaaS PM, no carbon background) understands within ~30 seconds *what problem this solves*, *what it can do*, and *why it's good* — then can try it without friction.

### B-1: Public marketing / landing page (pre-login front door)

**Goal:** Make `/` (logged-out) a real product landing page, not a login box. Login moves to `/login` only.

**Files:** new `frontend/src/app/(marketing)/page.tsx` (or restructure routing so logged-out root = landing); reuse design system.

**Page structure (Watershed/Linear editorial style):**
1. **Hero:** one-line value prop in plain language — e.g. *"Turn messy bills of materials into auditable product carbon footprints — and know exactly which suppliers to engage."* Subhead names the user (sustainability & business analysts). Primary CTA: "Try the live demo" (no signup) + secondary "Sign in."
2. **Problem framing:** 2–3 sentences on the pain (messy BOM data, Scope 3 Category 1, manual hotspot hunting).
3. **Core workflow snapshots:** 3–4 real product screenshots (BOM → factors → footprint → hotspots; the chat agent launching a module; supplier engagement email). Annotated. Use real UI, captured after Track A lands.
4. **Capability grid:** the 4–5 modules as cards, each with the *job it does* (not feature names).
5. **Trust band:** methodology callout — "Every number cites its source (Open CEDA 2025, GHG Protocol). Auditable by design." This is the differentiator for this buyer.
6. **Secondary CTA** + minimal footer.

**Verify:** Logged-out visit to `/` shows the landing page; CTAs route correctly; logged-in users skip to dashboard; responsive.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section B-1. Build a public marketing landing page as the logged-out root, with login moved to /login. Use the new design system. Sections: plain-language hero + value prop with "Try live demo" (no-signup) and "Sign in" CTAs; problem framing; 3–4 annotated workflow snapshots (placeholders now, real screenshots after Track A); a capability grid framing each module by the job it does; a methodology/trust band emphasizing source citations and GHG Protocol grounding; footer. Update the auth routing in app-shell.tsx so logged-out root = landing, logged-in root = dashboard.
```

---

### B-2: Dashboard module flip-cards ("what is this / why / how")

**Goal:** On the logged-in dashboard, each module is a **flip card** — front states the job in one line; on hover/focus it flips to reveal the problem it solves, what it does, and a CTA.

**Files:** new `frontend/src/components/dashboard/ModuleFlipCard.tsx`; update `frontend/src/app/page.tsx`.

**Content per card (front → back):**
- **Analyzer** — Front: "Estimate a product's footprint from its BOM." Back: the problem (messy BOM data, no easy Scope 3 number), what it does (parse → match factors → calculate → hotspots), CTA "Analyze a BOM."
- **Gap Analyzer** — Front: "Find what's missing in your Scope 3 data." Back: problem/what/CTA.
- **Supplier Copilot** — Front: "Engage the right suppliers first." Back: ...
- **Advisor / Chat** — Front: "Ask anything about your footprints & GHG Protocol." Back: ...

**Interaction details:** 3D flip on hover (desktop) and tap (mobile/touch), `prefers-reduced-motion` → cross-fade instead of flip, keyboard-focusable, back face fully accessible. Use the semantic palette sparingly per module for subtle differentiation.

**Verify:** Hover/tap each card flips smoothly; reduced-motion falls back to fade; keyboard focus flips; CTAs launch the right workflow via chat.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section B-2. Build ModuleFlipCard and use it on the dashboard. Front face: module name + one-line job. Back face (on hover desktop / tap mobile / focus keyboard): the problem it solves, what it does in 3 steps, and a CTA that launches the workflow. 3D flip with prefers-reduced-motion cross-fade fallback, fully keyboard accessible. Replace the current flat module cards on page.tsx with these.
```

---

### B-3: Consistent per-module intro pattern

**Goal:** Every module page opens with the same friendly, informative framing so users of any background can follow — without cluttering repeat use.

**Files:** new `frontend/src/components/modules/ModuleIntro.tsx`; apply to `analyzer/`, `gap-analysis/`, `advisor/`, `suppliers/`.

**Pattern:**
- A dismissible **intro header**: module name, one-line job, a 3-step "how it works" strip, and a "what you'll need" note (e.g. "a BOM CSV with component, material, quantity, spend").
- A **"?" help affordance** that re-opens the intro and links to a sample file / docs.
- State persisted (per user, per module) so it collapses to a slim bar after first use — informative for newcomers, unobtrusive for regulars.
- Tie in the **sample BOMs** (`sample_boms/`) as one-click "try with sample data."

**Verify:** First visit to each module shows the full intro; dismiss → slim bar; "?" reopens; "try sample" loads a sample BOM end-to-end.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section B-3. Build a reusable ModuleIntro component (name, one-line job, 3-step how-it-works, "what you'll need", a "try with sample data" button wired to sample_boms/, and a "?" to reopen). Apply to analyzer, gap-analysis, advisor, and suppliers pages. Persist dismissed state per user+module (collapse to a slim bar after first use). Keep it consistent across all modules.
```

---

### B-4: Interactive product demo / guided tour (no-signup)

**Goal:** A "Try the demo" experience that walks a visitor through the core workflow step-by-step with realistic seeded data — the classic SaaS "show, don't tell."

**Files:** new `frontend/src/app/demo/` route + a lightweight tour driver (e.g. a custom coachmark component or a small lib like `driver.js` / `react-joyride`); a seeded read-only dataset.

**Two layers (build B-4a then B-4b):**
- **B-4a — Guided product tour (coachmarks):** for logged-in first-run, a 4–6 step spotlight tour: "This is your dashboard → here's how you start a BOM analysis → here's where hotspots appear → here's the chat that runs everything." Skippable, resumable, shown once.
- **B-4b — No-signup interactive demo:** a `/demo` sandbox seeded with a realistic example product (e.g. the water bottle / t-shirt from `sample_boms/`) that runs the *real* BOM → factors → footprint → hotspots → supplier flow read-only, with "next step" guidance overlaid. Ends with a "Create your workspace" CTA. This is what the landing page "Try live demo" button opens.

**Verify:** First login triggers the coachmark tour (once, skippable). `/demo` runs the full seeded workflow without auth and converts to signup at the end.

**Prompt (B-4a):**
```
Read UI_UX_UPGRADE_PLAN.md, section B-4a. Add a first-run guided tour: a 4–6 step skippable, resumable coachmark/spotlight tour over the real dashboard and chat (start a BOM analysis → see hotspots → use the chat agent → find saved analyses). Show once per user (persist completion), with a "Replay tour" entry in the help/command menu.
```

**Prompt (B-4b):**
```
Read UI_UX_UPGRADE_PLAN.md, section B-4b. Build a no-signup /demo sandbox seeded with a realistic example product from sample_boms/. It runs the real BOM → match factors → footprint → hotspots → supplier-engagement flow in read-only mode with step-by-step guidance overlaid, ending in a "Create your workspace" CTA. Wire the landing page "Try live demo" button to it.
```

---

### B-5: Teaching empty states & contextual help

**Goal:** Turn every blank screen into a guide (complements A-5; this is the content/onboarding angle).

**Scope:**
- Dashboard with no analyses → a "start here" hero with the 3 fastest paths.
- Empty thread list, empty saved analyses, empty supplier list, empty org → each explains what will appear and how to create the first one.
- Inline **definitions on hover** for jargon (Scope 3, cradle-to-gate, emission factor, hotspot) via a `<Term>` tooltip component sourced from the glossary already in `CLAUDE.md`.
- A persistent, low-key **"Help / What is this?"** entry (command menu + header) that opens a concise capabilities overview.

**Verify:** A brand-new account sees guidance at every empty surface; hovering a jargon term shows a plain-language definition.

**Prompt:**
```
Read UI_UX_UPGRADE_PLAN.md, section B-5. Design teaching empty states for every empty surface (dashboard, threads, saved analyses, suppliers, org) — each with a one-line explanation and a primary CTA. Add a <Term> tooltip component that shows plain-language definitions for carbon jargon (Scope 3, cradle-to-gate, emission factor, hotspot, primary/secondary data) sourced from the glossary in CLAUDE.md, and use it across module intros and results. Add a "What is this?" capabilities overview reachable from the header and command menu.
```

---

## Sequencing & Branch Strategy

**Branch:** `feature/ui-ux-upgrade` off `main`. Sub-branches per step optional; squash-merge each step with a clear message.

**Critical path (do in order):**
```
A-1 (tokens)  ──►  A-2 (primitives)  ──►  A-3 (shell)
                          │
                          ├──►  A-4 (data viz)
                          └──►  A-5 (motion/states)

B track can start after A-2 (needs primitives), but:
  B-1 landing snapshots need A-1..A-5 done (real screenshots)
  B-2/B-3/B-5 only need A-1/A-2
  B-4 should come last (needs the real flows looking good)
```

**Recommended order:** A-1 → A-2 → A-3 → A-4 → A-5 → B-2 → B-3 → B-5 → B-1 → B-4a → B-4b.
(Design system first so onboarding is built on the finished look; landing/demo last so screenshots and flows are final.)

**Parallelization:** A-4 and A-5 can run in parallel after A-2. B-2/B-3/B-5 can run in parallel after A-2.

---

## Success Criteria

**Track A (feel):**
- No `backdrop-blur`, `glass-card`, or radial-gradient backgrounds remain.
- One restrained accent; semantic data palette pinned and used consistently for emissions.
- Real type scale with tabular figures on all numbers; numbers align in every table.
- Every async surface has a skeleton; every error has a styled retry; dark mode works on every page.
- `/styleguide` renders all primitives in all states, both themes.
- Subjective bar: a stranger would believe this is a funded, production SaaS — not a template.

**Track B (clarity):**
- A cold visitor on `/` understands the product in <30s (test with 3 people who lack carbon background).
- "Try live demo" runs the core flow with zero signup.
- Each module front-and-center explains its job; flip cards + intros are consistent.
- New accounts never hit an unexplained blank screen.
- Jargon is always one hover away from a plain-language definition.

---

## Out of Scope (for this plan)

- Backend/API changes (this is frontend + a possible read-only demo seed).
- New product features/modules (we're presenting and polishing what exists).
- Full design-token theming for white-label/multi-brand.
- Marketing site beyond the single landing page (no blog/pricing/etc.).
