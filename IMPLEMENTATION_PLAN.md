# Implementation Plan: Production Upgrade

This plan upgrades the Product Carbon Footprint Analyzer from a Streamlit prototype to a production application. Each phase has a clear deliverable and can be executed as a Claude Code CLI session.

Reference: `Architecture_Decisions.md` explains the WHY behind every choice below.

---

## Phase 1: FastAPI Backend Extraction

**Goal:** Extract all business logic from Streamlit pages into a standalone FastAPI API server. After this phase, the entire product works as API endpoints — no Streamlit dependency for logic.

**Steps:**
1. Create `api/` directory at project root
2. Create `api/main.py` — FastAPI app with CORS, health check endpoint
3. Create `api/routes/analyzer.py` — endpoints for BOM upload, analysis, results
   - `POST /api/analyze` — accepts BOM file, returns analysis
   - `GET /api/analyses/{id}` — get saved analysis
   - `GET /api/analyses` — list all analyses
4. Create `api/routes/gap_analyzer.py` — endpoints for gap analysis workflow
   - `POST /api/gap-analysis/plan` — generate execution plan
   - `POST /api/gap-analysis/execute` — execute plan (refactor to LangGraph in Phase 2)
   - `POST /api/gap-analysis/approve` — human approval checkpoint
5. Create `api/routes/advisor.py` — endpoint for conversational advisor
   - `POST /api/advisor/chat` — send message, get response
6. Create `api/routes/copilot.py` — endpoints for supplier engagement
   - `POST /api/copilot/draft-email` — draft supplier outreach email
   - `POST /api/copilot/route-response` — classify and route supplier response
7. Move all `st.session_state` logic into Pydantic models in `api/models/`
8. Add `requirements-api.txt` with fastapi, uvicorn, pydantic additions
9. Test every endpoint manually via FastAPI's `/docs` page

**Verify:** Run `uvicorn api.main:app --reload` and hit every endpoint from the Swagger UI.

**Prompt to use:**
```
Read the IMPLEMENTATION_PLAN.md and Architecture_Decisions.md first. We're executing Phase 1: FastAPI Backend Extraction. Extract all business logic from the Streamlit pages (app.py, pages/1_Advisor.py, pages/2_Gap_Analyzer.py, pages/3_Supplier_Copilot.py) into FastAPI endpoints under api/. Keep the existing Streamlit app working — don't delete it, just create the parallel API layer. The business logic in calc/, factors/, parsing/, llm/, rag/, gap_analyzer/, copilot/, db/ stays where it is — the API routes import from those modules.
```

---

## Phase 2: LangGraph Refactor

**Goal:** Replace the Gap Analyzer's manual planner-executor with a LangGraph StateGraph, and refactor the Supplier Copilot's 4-phase workflow into a second LangGraph graph. Add LangSmith tracing.

**Steps:**
1. Create `api/graphs/gap_analyzer_graph.py`
   - StateGraph with nodes: plan, execute_tool (looped), human_review, save_results
   - Use `interrupt_before` at human_review node
   - Checkpointer for state persistence (PostgresSaver once Supabase is set up, MemorySaver for now)
2. Create `api/graphs/supplier_copilot_graph.py`
   - StateGraph with nodes: select_supplier, draft_email, human_review_email, send_email, process_response, route_response
   - The exception_router.py logic becomes a conditional edge
   - `interrupt_before` at human_review_email and at route_response decision points
3. Add LangSmith environment variables to `.env.example`
   - `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT=carbon-footprint-analyzer`
4. Update API routes to invoke graphs instead of direct function calls
5. Add streaming support — SSE endpoint that streams graph state updates

**Verify:** Run a gap analysis through the API. Check LangSmith dashboard for traces showing the full node execution tree.

**Prompt to use:**
```
Read IMPLEMENTATION_PLAN.md and Architecture_Decisions.md. We're executing Phase 2: LangGraph Refactor. Look at the existing gap_analyzer/planner.py, gap_analyzer/executor.py, copilot/draft_email.py, and copilot/exception_router.py. Refactor the Gap Analyzer into a LangGraph StateGraph in api/graphs/gap_analyzer_graph.py. The planner becomes a node, each tool execution is a node in a loop, and human review is an interrupt_before checkpoint. Then do the same for the Supplier Copilot workflow. Add LangSmith tracing (just env vars — it auto-traces LangGraph). Update the API routes to use the graphs.
```

---

## Phase 3: Supabase Migration

**Goal:** Replace SQLite with Supabase Postgres. Add auth. Set up Row-Level Security.

**Steps:**
1. Create Supabase project (manual — do this in the Supabase dashboard first)
2. Create database migrations in `supabase/migrations/`
   - `001_create_analyses.sql` — product analyses table
   - `002_create_supplier_engagements.sql` — supplier engagement records
   - `003_create_audit_log.sql` — audit trail
   - `004_enable_rls.sql` — Row-Level Security policies
3. Replace `db/store.py` and `db/reader.py` with Supabase client calls
   - Use `supabase-py` for the Python backend
   - Or use `asyncpg` / `sqlalchemy[asyncio]` with the Postgres connection string
4. Add Supabase Auth middleware to FastAPI
   - Verify JWT on every request
   - Extract user_id for RLS
5. Update `.env.example` with Supabase vars
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`
6. Update LangGraph checkpointer from MemorySaver to PostgresSaver (uses same Supabase Postgres)

**Verify:** Create a user account, run an analysis, verify data appears in Supabase dashboard with correct user_id. Verify a second user can't see the first user's data.

**Prompt to use:**
```
Read IMPLEMENTATION_PLAN.md and Architecture_Decisions.md. We're executing Phase 3: Supabase Migration. I've already created a Supabase project. Here are my credentials: [paste SUPABASE_URL and keys]. Create the database migrations in supabase/migrations/. Replace the SQLite store (db/store.py and db/reader.py) with Supabase Postgres using supabase-py or asyncpg. Add auth middleware to the FastAPI app that verifies Supabase JWTs. Set up RLS so each user only sees their own data.
```

---

## Phase 4: Next.js Frontend

**Goal:** Build a Next.js frontend that replaces Streamlit. Deploy to Vercel.

**Steps:**
1. Create `frontend/` directory, initialize Next.js with TypeScript, Tailwind, shadcn/ui
2. Set up Supabase Auth in the frontend (login/signup pages)
3. Build pages:
   - `app/page.tsx` — Dashboard (list of saved analyses, quick stats)
   - `app/analyzer/page.tsx` — BOM upload and analysis workflow
   - `app/analyzer/[id]/page.tsx` — View saved analysis with charts
   - `app/gap-analysis/page.tsx` — Gap analyzer with plan/execute/review flow
   - `app/advisor/page.tsx` — Chat interface for conversational advisor
   - `app/suppliers/page.tsx` — Supplier engagement copilot
4. API client layer in `frontend/lib/api.ts` — typed fetch wrappers for all FastAPI endpoints
5. Real-time updates: SSE or polling for long-running LangGraph operations
6. Loading states, error boundaries, responsive design
7. Deploy to Vercel — connect GitHub repo, set environment variables

**Verify:** Open the Vercel URL. Log in, upload a BOM, run analysis, use the advisor chat, run gap analysis with human checkpoint, draft a supplier email.

**Prompt to use:**
```
Read IMPLEMENTATION_PLAN.md and Architecture_Decisions.md. We're executing Phase 4: Next.js Frontend. Create a frontend/ directory. Initialize Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui. Set up Supabase Auth (login/signup). Build the main pages: dashboard, analyzer (BOM upload + results), gap analysis (with human-in-the-loop checkpoints), advisor (chat), and supplier copilot. The frontend calls the FastAPI backend at [BACKEND_URL] for all AI operations and uses Supabase directly for auth and simple data reads. Make it look professional — proper loading states, error handling, responsive layout.
```

---

## Phase 5: Evals, CI, and Polish

**Goal:** Add eval pipeline, CI/CD, README, and production polish.

**Steps:**
1. Create `evals/` directory
   - `evals/golden_files/` — test cases from Specs/ (clean, messy, edge case BOMs)
   - `evals/test_golden_files.py` — pytest tests that run analyses and assert invariants
   - `evals/llm_judge.py` — LLM-as-judge eval for advisor responses and email quality
2. Create `.github/workflows/ci.yml`
   - Run golden-file tests on every PR
   - Run ruff linting
   - Type checking (mypy or pyright for backend, tsc for frontend)
3. Create `.github/workflows/eval.yml`
   - Run LLM-as-judge evals nightly (scheduled workflow)
   - Post results to LangSmith
4. Write README.md
   - Project description, architecture diagram (Mermaid), setup instructions
   - Link to live deployment
   - Section on eval strategy and observability approach
5. Git hygiene: create feature branches for remaining work
6. Deploy backend to Railway, frontend to Vercel, verify end-to-end

**Prompt to use:**
```
Read IMPLEMENTATION_PLAN.md and Architecture_Decisions.md. We're executing Phase 5: Evals, CI, and Polish. Create an evals/ directory with golden-file tests using the test cases from Specs/ — each test runs a BOM through the analyzer and asserts the eval invariants from Claude.md (total = sum of line items, sources cited, same input = same output). Add an LLM-as-judge eval for advisor and email quality. Set up GitHub Actions CI that runs these tests on every PR. Write a proper README.md with architecture diagram, setup instructions, and a section explaining the eval strategy.
```

---

## Phase 6: Platform Chat Agent

**Goal:** Convert the Advisor chat into a central Platform Chat Agent that orchestrates the entire product — users can start any workflow, query any data, and navigate any module through a single conversational interface.

This is a large feature with its own detailed plan. See **`PLATFORM_CHAT_AGENT_PLAN.md`** for:
- Full design decisions (interaction model, skills architecture, memory layers, multi-tenancy)
- Database schema changes (chat threads, semantic memory, org tables, active panels)
- Four sub-phases (6A: Backend skills/memory, 6B: Frontend chat/panels, 6C: Semantic memory/orgs, 6D: Entry points/polish)
- Prompts for each sub-phase

---

## Order of Operations

```
Phase 1 (FastAPI)  ──> Phase 2 (LangGraph) ──> Phase 3 (Supabase)
                                                       |
                                                       v
                                              Phase 4 (Next.js)
                                                       |
                                                       v
                                              Phase 5 (Evals + CI)
                                                       |
                                                       v
                                              Phase 6 (Platform Chat Agent)
                                                 6A ──> 6B ──> 6C ──> 6D
```

Phases 1-3 are backend. Phase 4 is frontend. Phase 5 is polish. Phase 6 is the chat agent. Each phase produces a working, testable artifact.

---

## How to Start Each Phase in Claude Code CLI

```bash
cd "/Users/raaglavingiya/Downloads/Claude Practice project/product-footprint-analyzer"
claude
```

Then paste the phase's prompt. Claude Code will read the plan and architecture docs and start building.

Between phases, commit your work:
```bash
git add -A && git commit -m "Phase N: [description]"
```

Better yet, commit at sub-phase boundaries (after each major feature within a phase) using meaningful messages.
