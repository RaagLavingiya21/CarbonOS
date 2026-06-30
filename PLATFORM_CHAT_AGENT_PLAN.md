# Implementation Plan: Platform Chat Agent

This plan adds a central Platform Chat Agent that becomes the primary way users interact with the product. It converts the existing Advisor chat from a single module into the orchestration layer for the entire platform.

Reference: This plan was designed through a collaborative design session. See `IMPLEMENTATION_PLAN.md` for the preceding production upgrade phases (1–5).

---

## Design Decisions Summary

These decisions were made during the design session and should not be revisited without good reason.

### Core interaction model
- The chat is a **conversational launcher and navigator** — it collects inputs through inline forms, then opens the appropriate module panel
- **Two entry paths** into any module: (a) click a static module button below chat input → skip intent router → show intake form, (b) type free text → intent router classifies → show intake form
- The chat uses **predefined intake form templates** per module (not LLM-generated forms)
- After intake, the module opens in a panel **to the right of chat**, already past the intake step (e.g., BOM Analyzer opens at the review checkpoint)
- The chat sends a **confirmation message** when a module panel opens ("I've opened the BOM Analyzer with your file. Review the parsed data in the panel on the right.")

### Module panels
- Each new module call opens **its own panel** to the right of chat
- Within each panel, **browser-style tabs** let the user switch between multiple instances (e.g., two BOM analyses)
- The **most recently called** module panel is visible; others are accessible via tabs
- Panels **persist across page refresh** (state stored in database)

### Intake form templates (predefined)
| Module | Fields |
|--------|--------|
| BOM Analyzer | File upload + product name (text) |
| Gap Analyzer | Company name, size (dropdown), sector (text), geography (text), products (textarea) |
| Supplier Copilot | Product selection (dropdown from saved analyses) + top N suppliers (number) |
| Advisor | No intake form — free-text Q&A |

### Chat history
- All chat threads are **saved to database** — users can access old threads
- Thread titles are **auto-generated** from the first message (heuristic or short LLM call)
- **Single continuous thread** per conversation — no splitting by module
- **Context management**: keep last 10 messages verbatim, summarize older messages into a rolling summary paragraph
- When a user makes a similar request within the same thread, **summarize prior context** rather than replaying it

### Contextual suggestions
- **Static module buttons** always visible below chat input (BOM Analyzer, Gap Analyzer, Supplier Copilot, Advisor)
- After each agent response, show **2–3 generic next-step suggestions** (e.g., "Start supplier engagement", "Run gap analysis") so users can continue the workflow without typing
- Suggestions are **generic for now** — not deeply personalized to specific product data

### Out-of-scope requests
- System prompt guards chat to platform-relevant topics only
- Off-topic requests get a friendly redirect: "Here's what I can help you with" + module buttons
- **Deferred**: fine-tuning the exact boundary of what's in/out of scope

### Entry points (later phase)
- Home page: ChatGPT-style central chat bar
- Global: top-right AI/intelligence icon accessible from any page
- These are cosmetic — build the agent and panel system first

---

## Agent Architecture

### Skills (not raw tools)

The agent routes to **4 skills**, not 15+ individual tools. Each skill encapsulates multiple internal operations. This keeps LLM routing accurate (4 choices, not 15) and makes it easy to add capabilities without changing the system prompt.

| Skill | Responsibility | Internal operations |
|-------|---------------|---------------------|
| **Analysis** | Everything related to product footprint data and launching analysis modules | Get product details, list products, compare products, search line items, get hotspots, launch BOM module, launch gap module |
| **Guidance** | GHG Protocol knowledge and methodology questions | RAG retrieval, query expansion, cite GHG sections, answer methodology, domain Q&A |
| **Engagement** | Supplier-related workflows | List engagements, draft email, parse response, supplier lookup, launch copilot module |
| **Memory** | Context retrieval — user data, org data, history | Read/write user memory, read org context, search org data, get team activity, summarize history |

### Memory layers (progressive disclosure)

The agent does NOT load all user data into the system prompt. Context is loaded in layers, from always-present to on-demand:

| Layer | What | When loaded | Size |
|-------|------|-------------|------|
| **1. System prompt** | Agent identity, skill descriptions, guardrails, domain basics | Every turn | ~2,000 tokens |
| **2. User profile summary** | Lightweight summary: product names + totals, engagement count, org membership. No line-item details. | Once per session, refreshed on major state change | ~300 tokens |
| **3. Semantic memory** | Cross-session user knowledge and preferences (e.g., "user focused on packaging reduction", "prefers metric tons"). Also org-level memory (e.g., "Acme Corp targeting 30% Scope 3 reduction by 2030"). | Once per session | ~200 tokens |
| **4. Skill calls (on-demand)** | Full product details, line items, gap analysis results, RAG chunks, engagement data | Only when a skill is invoked | Variable |
| **5. Conversation history** | Last 10 messages verbatim + rolling summary of older messages | Every turn | Managed |

**Key principle**: Layers 1–3 give the agent enough awareness to route correctly and sound knowledgeable. Layer 4 provides depth only when needed. Layer 5 maintains conversational coherence.

### Semantic memory design

Two scopes of semantic memory:

- **User memory**: preferences, focus areas, working patterns. Written by the agent (inferred from conversations) and by the system (from user actions). Example: "User is focused on reducing cotton fabric emissions across product line."
- **Org memory**: company context, targets, shared knowledge. Written by any team member, visible to all. Example: "Acme Corp is an apparel manufacturer targeting 30% Scope 3 reduction by 2030."

### Teams / multi-tenancy model

- **Visibility**: everyone on a team sees everything (all analyses, all engagements, all org memory). No role-based access control for now.
- **Agent context**: the user profile summary (Layer 2) includes both personal and org-level summaries: "You have personally analyzed 3 products. Your organization has 47 analyzed products across 4 team members."
- **Disambiguation**: when a user says "our products," the agent defaults to **org-wide** and lets the user narrow down.
- **Org-scoped queries**: the Memory skill queries with `org_id` by default for data questions, `user_id` for personal preference questions.

---

## Database Schema Changes

### New tables

```sql
-- Chat threads
CREATE TABLE chat_threads (
    thread_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID REFERENCES organizations(id),
    title TEXT,                           -- auto-generated from first message
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Chat messages
CREATE TABLE chat_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES chat_threads(thread_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',          -- module launched, intake form data, skill used
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Semantic memory (user-level)
CREATE TABLE user_memory (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    content TEXT NOT NULL,
    category TEXT NOT NULL,               -- 'preference', 'focus_area', 'working_pattern'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Semantic memory (org-level)
CREATE TABLE org_memory (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    created_by UUID NOT NULL REFERENCES auth.users(id),
    content TEXT NOT NULL,
    category TEXT NOT NULL,               -- 'company_context', 'target', 'shared_knowledge'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Active module panels (for persistence across refresh)
CREATE TABLE active_panels (
    panel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    thread_id UUID REFERENCES chat_threads(thread_id),
    module_type TEXT NOT NULL,            -- 'bom_analyzer', 'gap_analyzer', 'supplier_copilot', 'advisor'
    panel_state JSONB DEFAULT '{}',       -- module-specific state (current step, data)
    tab_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,       -- most recently opened
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Organizations (if not already present)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Org membership
CREATE TABLE org_members (
    user_id UUID NOT NULL REFERENCES auth.users(id),
    org_id UUID NOT NULL REFERENCES organizations(id),
    role TEXT DEFAULT 'member',
    PRIMARY KEY (user_id, org_id)
);
```

### RLS policies
- `chat_threads`: user sees own threads only
- `chat_messages`: user sees messages in own threads only
- `user_memory`: user sees own memory only
- `org_memory`: user sees memory for their org
- `active_panels`: user sees own panels only
- Products, line_items, supplier_engagements: update RLS to allow org-wide visibility (query by `org_id` through `org_members`)

---

## Implementation Phases — Broken Into Small Features

Each step below is sized for a **single coding session** (~1-2 hours). Complete and test each step before starting the next. Steps within a phase are sequential; some steps across phases can overlap where noted.

---

### Phase 6A: Backend Foundation

#### 6A-1: Database migrations — chat and org tables

**Goal:** Create the database tables for chat threads, messages, organizations, and org membership. No application code yet — just the schema.

**Files to create:**
- `supabase/migrations/010_create_organizations.sql` — organizations + org_members tables
- `supabase/migrations/011_create_chat_tables.sql` — chat_threads + chat_messages tables
- `supabase/migrations/012_create_memory_tables.sql` — user_memory + org_memory tables
- `supabase/migrations/013_create_active_panels.sql` — active_panels table
- `supabase/migrations/014_chat_rls_policies.sql` — RLS policies for all new tables

**Verify:** Run migrations against Supabase. Check tables exist in the dashboard. Verify RLS blocks cross-user access.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, specifically the "Database Schema Changes" section. Create Supabase migrations for the 7 new tables (organizations, org_members, chat_threads, chat_messages, user_memory, org_memory, active_panels). Include RLS policies: users see own threads/messages/panels/user_memory; org_memory visible to org members; chat_messages scoped through thread ownership. Follow the existing migration pattern in supabase/migrations/.
```

---

#### 6A-2: DB CRUD layer for chat and memory

**Goal:** Python modules for reading/writing chat threads, messages, and memory. Pure data access — no agent logic.

**Files to create:**
- `db/chat_store.py` — create/list/get/delete threads; create/list messages for a thread
- `db/memory_store.py` — create/list/update/delete user_memory and org_memory entries
- `db/panel_store.py` — create/list/update/delete active_panels
- `db/org_store.py` — create org, add/remove members, get user's org

**Verify:** Write a small test script that creates a thread, adds messages, reads them back. Create a memory entry, read it. All operations should work with Supabase auth tokens.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Create the data access layer for the new tables. Follow the existing patterns in db/store.py and db/reader.py — use get_user_client(access_token) from db/client.py, return dataclasses or dicts. Create db/chat_store.py (thread and message CRUD), db/memory_store.py (user and org memory CRUD), db/panel_store.py (active panel CRUD), and db/org_store.py (org and membership CRUD). No agent logic — just clean data access functions.
```

---

#### 6A-3: Analysis and Guidance skills

**Goal:** Build the first two skills that wrap existing business logic. Each skill is a Python class with a `run()` method and a schema describing its capabilities.

**Files to create:**
- `api/skills/base.py` — base Skill class with `name`, `description`, `parameters_schema`, and `run()` method
- `api/skills/analysis.py` — wraps `db/reader.py` for product data queries (list products, get details, get hotspots, compare products)
- `api/skills/guidance.py` — wraps `rag/retriever.py` and the existing advisor logic for GHG Protocol Q&A

**Verify:** Import each skill in a Python REPL. Call `analysis_skill.run(action="list_products", access_token=token)` and verify it returns product data. Call `guidance_skill.run(action="ask", query="What is Scope 3?")` and verify it returns RAG-grounded answer.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, specifically the "Skills" section. Create api/skills/base.py with a base Skill class (name, description, parameters_schema as a JSON schema dict, and an async run() method). Then create api/skills/analysis.py — it wraps db/reader.py to support actions: list_products, get_product_details, get_hotspots, compare_products. Each action queries the DB and returns a formatted dict. Then create api/skills/guidance.py — it wraps rag/retriever.py and the existing advisor pattern from llm/client.py for RAG-based Q&A. Don't duplicate business logic — import from existing modules. Each skill must work standalone without the agent.
```

---

#### 6A-4: Engagement and Memory skills

**Goal:** Build the remaining two skills.

**Files to create:**
- `api/skills/engagement.py` — wraps `copilot/` for supplier operations (list candidates, get engagement status, draft email trigger)
- `api/skills/memory.py` — reads/writes user and org memory via `db/memory_store.py`, builds profile summaries
- `api/skills/registry.py` — registry that maps skill names to instances, provides schemas for the LLM system prompt

**Verify:** Call each skill's `run()` method directly. Verify the registry returns all 4 skills with their schemas.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Create api/skills/engagement.py — wraps copilot/suppliers_list.py and copilot/draft_email.py. Actions: list_engagement_candidates (for a product), get_engagement_status, trigger_email_draft. Then create api/skills/memory.py — wraps db/memory_store.py. Actions: read_user_memory, write_user_memory, read_org_memory, write_org_memory, build_profile_summary (generates the Layer 2 context string from DB data). Finally create api/skills/registry.py — a SkillRegistry class that holds all 4 skills, provides get_all_schemas() for the system prompt, and get_skill(name) for execution. Follow the base class pattern from api/skills/base.py.
```

---

#### 6A-5: Agent core — system prompt and intent router

**Goal:** Build the LangGraph agent graph that processes user messages. This is the brain — it assembles context, routes to skills, and generates responses.

**Files to create:**
- `api/agent/system_prompt.py` — builds the system prompt dynamically from Layers 1+2+3, includes skill schemas as tool definitions
- `api/agent/intent_router.py` — single LLM call with tools (the 4 skills); Claude decides which skill to call or answers directly
- `api/agent/graph.py` — LangGraph StateGraph with nodes: build_context → route_intent → execute_skill (conditional) → generate_suggestions → save_to_history
- `api/agent/state.py` — TypedDict for the graph state (messages, active_skill, skill_result, suggestions, module_launch, etc.)
- `api/agent/intake_forms.py` — predefined form template data structures per module

**Also in this step:** Create the API endpoints for chat and panels. These are thin wrappers — thread/message CRUD calls `db/chat_store.py`, the send-message endpoint invokes the graph, and panel CRUD calls `db/panel_store.py`. No reason to make a separate step for boilerplate REST routes.

**Files to also create:**
- `api/routes/chat.py` — POST/GET/DELETE for threads; POST for send message (invokes graph)
- `api/routes/panels.py` — GET/POST/PATCH/DELETE for panels
- Update `api/main.py` to include both new routers

**Verify:** Import the graph and invoke it with a test message. Verify "list my products" routes to Analysis skill. Verify "what is Scope 3?" routes to Guidance skill. Verify "hello" gets a direct answer without a skill call. Verify off-topic "write me a poem" gets the guardrail response. Also verify via FastAPI `/docs`: create a thread, send a message, get a response. Create/list/update/delete a panel.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, specifically "Agent Architecture" and the LangGraph structure. Create the agent core AND the API endpoints (they're tested together):

1. api/agent/state.py — TypedDict for graph state: messages (list), user_id, access_token, context_layers (dict), active_skill (str|None), skill_result (dict|None), suggestions (list[str]), module_launch (dict|None), thread_id.

2. api/agent/system_prompt.py — build_system_prompt(user_id, access_token) that assembles Layer 1 (static identity + guardrails + skill descriptions from registry), Layer 2 (profile summary from Memory skill), Layer 3 (semantic memories from db/memory_store.py). Return a single string.

3. api/agent/intent_router.py — makes one Claude claude-sonnet-4-6 call with the 4 skills as tools. If Claude calls a tool, return the skill name + parameters. If Claude responds directly, return the text. Use the Anthropic SDK pattern from llm/client.py.

4. api/agent/graph.py — LangGraph StateGraph: build_context node → route_intent node → conditional edge (skill called? → execute_skill node, else → format_response node) → generate_suggestions node → save_to_history node → END. Use PostgresSaver checkpointer.

5. api/agent/intake_forms.py — dict mapping module names to their form schemas: bom_analyzer (file_upload + product_name), gap_analyzer (company_name, size, sector, geography, products), supplier_copilot (product_id + top_n).

6. api/routes/chat.py — POST /api/chat/threads (create), GET /api/chat/threads (list), GET /api/chat/threads/{thread_id} (get with messages), POST /api/chat/threads/{thread_id}/messages (send message → invoke graph → return response + suggestions + module_launch), DELETE /api/chat/threads/{thread_id}.

7. api/routes/panels.py — GET /api/panels (list), POST /api/panels (create with module_type + thread_id + initial state), PATCH /api/panels/{panel_id} (update state + tab_order), DELETE /api/panels/{panel_id}.

8. Update api/main.py to include both new routers.

Use LangGraph's StateGraph and add_node/add_edge pattern. Use Pydantic models for request/response schemas. Follow existing route patterns for auth.
```

---

### Phase 6B: Frontend — Chat UI

#### 6B-1: Basic chat interface (no panels yet)

**Goal:** A working chat page where the user can type messages and get agent responses. Full-width, no split screen yet.

**Files to create:**
- `frontend/app/chat/page.tsx` — chat page layout
- `frontend/components/chat/ChatThread.tsx` — scrollable message list
- `frontend/components/chat/ChatMessage.tsx` — single message bubble (user vs assistant styling)
- `frontend/components/chat/ChatInput.tsx` — text input with send button
- `frontend/lib/chat-api.ts` — typed API client for chat endpoints

**Verify:** Open `/chat` in the browser. Type a message, see the agent respond. Messages persist on page refresh (loaded from API). Multiple messages in a conversation work.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. We're building the basic chat UI — no panels or module buttons yet, just a working chat.

Create frontend/app/chat/page.tsx — a full-width chat page. Create frontend/components/chat/ChatThread.tsx (scrollable message list, auto-scrolls to bottom), ChatMessage.tsx (message bubble with user/assistant styling, renders markdown), ChatInput.tsx (text input with send button, disabled while waiting for response). Create frontend/lib/chat-api.ts with typed functions for createThread, listThreads, getThread, sendMessage.

On first visit, auto-create a new thread. Messages should show a loading indicator while the agent responds. Use shadcn/ui components and the existing Supabase auth setup for the access token.
```

---

#### 6B-2: Module buttons and suggestion chips

**Goal:** Add static module buttons below the chat input and contextual suggestion chips after agent responses.

**Files to create/modify:**
- `frontend/components/chat/ModuleButtons.tsx` — row of 4 buttons (BOM Analyzer, Gap Analyzer, Supplier Copilot, Advisor)
- `frontend/components/chat/SuggestionChips.tsx` — clickable chip row shown after assistant messages
- Update `ChatInput.tsx` to include ModuleButtons below the input
- Update `ChatMessage.tsx` to render SuggestionChips after assistant messages

**Verify:** Module buttons appear below the chat input. Clicking one sends a predefined message (e.g., "I want to analyze a BOM"). Suggestion chips appear after agent responses. Clicking a chip sends it as a message.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Add module buttons and suggestion chips to the chat UI.

Create frontend/components/chat/ModuleButtons.tsx — a horizontal row of 4 buttons: "Analyze BOM" (icon: file-upload), "Gap Analysis" (icon: search), "Supplier Engagement" (icon: mail), "Ask Advisor" (icon: message-circle). Clicking a button sends a predefined message to the chat (e.g., clicking "Analyze BOM" sends "I want to analyze a bill of materials"). Style as outlined pill buttons using shadcn/ui Button variant="outline".

Create frontend/components/chat/SuggestionChips.tsx — renders a list of suggestion strings as small clickable chips. Clicking sends the text as a user message. The suggestions come from the agent response API (the suggestions field).

Update ChatInput to show ModuleButtons below it. Update ChatMessage to show SuggestionChips after assistant messages when suggestions are present.
```

---

#### 6B-3: Inline intake forms

**Goal:** When the agent determines a module should launch, it returns a form template. The chat renders it as an interactive form inside a message bubble.

**Files to create:**
- `frontend/components/chat/forms/IntakeFormMessage.tsx` — wrapper that renders the right form based on module_type
- `frontend/components/chat/forms/BOMIntakeForm.tsx` — file upload + product name text field
- `frontend/components/chat/forms/GapAnalyzerIntakeForm.tsx` — company name, size dropdown, sector, geography, products textarea
- `frontend/components/chat/forms/SupplierCopilotIntakeForm.tsx` — product dropdown (from saved analyses) + top N number input
- Update `ChatMessage.tsx` to detect intake form metadata and render IntakeFormMessage

**Verify:** Type "I want to analyze a BOM." Agent responds with an intake form in the chat. Fill in the product name and upload a file. Click submit. The form data is sent back to the agent as a structured message. Repeat for Gap Analyzer and Supplier Copilot forms.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, specifically the "Intake form templates" section. Build inline forms that render inside chat message bubbles.

Create frontend/components/chat/forms/IntakeFormMessage.tsx — receives module_type from the message metadata, renders the matching form component. Create BOMIntakeForm.tsx (shadcn file upload + text input for product name + submit button), GapAnalyzerIntakeForm.tsx (5 fields: company name text, size Select dropdown with options "1-100"/"100-500"/"500-5000"/"5000+", sector text, geography text, products Textarea + submit), SupplierCopilotIntakeForm.tsx (product Select dropdown populated from GET /api/analyses + number input for top_n + submit).

Each form on submit calls sendMessage with a structured JSON payload in the content. Update ChatMessage.tsx — when a message has metadata.intake_form, render IntakeFormMessage instead of plain text. Style forms with a subtle card background inside the message bubble.
```

---

#### 6B-4: Split-screen layout and panel container

**Goal:** When a module launches, the layout splits — chat on the left, module panel on the right.

**Files to create:**
- `frontend/components/layout/SplitLayout.tsx` — flexbox layout: chat area (resizable) + panel area
- `frontend/components/panels/PanelContainer.tsx` — right-side container that shows the active panel
- `frontend/components/panels/PanelTabs.tsx` — browser-style tab bar for switching between open panels
- Update `frontend/app/chat/page.tsx` to use SplitLayout

**Verify:** Chat starts full-width. When a module launches (from agent response), the layout animates to split view. The panel area shows a placeholder with the module name. Tab bar appears when 2+ panels are open. Clicking tabs switches the visible panel. Closing a tab removes the panel. When all panels are closed, chat returns to full-width.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Build the split-screen layout and panel system.

Create frontend/components/layout/SplitLayout.tsx — a flex container with two children: chat area and panel area. When no panels are open, chat takes 100% width. When a panel is open, animate to 40% chat / 60% panel (use CSS transition). Add a draggable divider between them for manual resizing (store width in localStorage).

Create frontend/components/panels/PanelContainer.tsx — renders the active panel content. For now, show a placeholder card with the module name and a close button. Create frontend/components/panels/PanelTabs.tsx — a horizontal tab bar (like browser tabs) showing all open panels. Each tab has a label (module name) and close button. Active tab is highlighted. Clicking a tab switches the visible panel.

Create a PanelContext (React context + provider) to manage panel state: openPanels array, activePanel, openPanel(module_type, state), closePanel(panel_id), switchPanel(panel_id). Wire this into the chat page — when the agent response includes module_launch, call openPanel().
```

---

#### 6B-5: Module panel content (BOM + Gap Analyzer)

**Goal:** Replace the placeholder panels with actual module content. Start with the two most-used modules.

**Files to create:**
- `frontend/components/panels/BOMPanel.tsx` — embeds the BOM analyzer workflow starting at the BOM review step (data already parsed from intake form)
- `frontend/components/panels/GapAnalyzerPanel.tsx` — embeds the gap analyzer workflow (company profile already collected from intake form)

**Verify:** Complete the BOM intake form in chat. Panel opens with parsed BOM data at the review step. User can proceed through the remaining checkpoints (EF review → results) inside the panel. Complete the Gap Analyzer intake form in chat. Panel opens with the gap analysis running.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Build the BOM and Gap Analyzer panel content.

Create frontend/components/panels/BOMPanel.tsx. It receives the intake form data (uploaded file + product name) via panel state. On mount, it calls POST /api/analyze with the file to get the parsed BOM. Then it renders the BOM review step (table of parsed rows with flags). The user can proceed through EF review and results steps — reuse or adapt the existing analyzer page components if they exist in frontend/. Each step calls the appropriate API endpoint.

Create frontend/components/panels/GapAnalyzerPanel.tsx. It receives the company profile from intake form data. On mount, it calls POST /api/gap-analysis/plan to generate the analysis plan. Then it renders the plan and execution steps with human checkpoints — reuse or adapt existing gap analyzer page components.

Both panels should update their panel_state via PATCH /api/panels/{id} as the user progresses through steps, so state persists on refresh.
```

---

#### 6B-6: Supplier Copilot panel and panel persistence

**Goal:** Build the last module panel and add persistence across page refresh.

**Files to create:**
- `frontend/components/panels/SupplierCopilotPanel.tsx` — embeds the supplier engagement workflow
- Update `PanelContext` to sync with the panels API (load on mount, save on change)

**Verify:** Complete the Supplier Copilot intake form. Panel opens with ranked suppliers. User can proceed to draft emails. Refresh the page — all open panels restore with their current step. Close all panels — chat returns to full-width.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Build the Supplier Copilot panel and add persistence.

Create frontend/components/panels/SupplierCopilotPanel.tsx. It receives product_id + top_n from intake. On mount, calls the supplier candidates API. Renders the ranked list. User can click "Draft email" on any candidate to trigger email drafting. Reuse existing copilot page components where possible.

Update PanelContext to persist: on mount, call GET /api/panels to restore open panels. On openPanel(), call POST /api/panels. On state change within a panel, debounce PATCH /api/panels/{id}. On closePanel(), call DELETE /api/panels/{id}. This ensures panels survive page refresh and browser close.
```

---

#### 6B-7: Chat thread history sidebar

**Goal:** Users can see and switch between saved chat threads.

**Files to create:**
- `frontend/components/chat/ThreadList.tsx` — sidebar list of threads with titles and dates
- `frontend/components/chat/ThreadListItem.tsx` — single thread row with title, date, delete button
- Update `frontend/app/chat/page.tsx` to include the sidebar (collapsible)

**Verify:** Start multiple chat threads. Thread list shows all of them with auto-generated titles. Click a thread to load its messages. Delete a thread. New chat button creates a fresh thread.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Build the chat history sidebar.

Create frontend/components/chat/ThreadList.tsx — a collapsible sidebar on the left edge of the chat area. Shows a "New chat" button at top, then a list of threads from GET /api/chat/threads (newest first). Each item shows the thread title and relative date ("2 hours ago"). Create ThreadListItem.tsx — single row with title, date, and a delete button (visible on hover). Clicking a thread loads its messages into ChatThread. Clicking "New chat" creates a new thread via POST /api/chat/threads.

Add a toggle button to collapse/expand the sidebar. When collapsed, show just a narrow strip with a menu icon. Store collapsed state in localStorage.
```

---

### Phase 6C: Intelligence Layer

#### 6C-1: Conversation summarization

**Goal:** When conversations get long, summarize older messages to keep the context window manageable.

**Files to create/modify:**
- `api/agent/context_manager.py` — manages the sliding window: keeps last 10 messages verbatim, summarizes older ones via a short LLM call, stores the rolling summary

**Verify:** Have a 15+ message conversation. Verify the agent still remembers early context (from the summary). Check that the LLM call token count stays bounded — it shouldn't grow linearly with conversation length.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, specifically "Context management" in Layer 5. Create api/agent/context_manager.py with a function build_conversation_context(thread_id, access_token) that: (1) fetches all messages for the thread, (2) if >10 messages, takes the oldest messages and summarizes them into a single paragraph via a short Claude claude-haiku-4-5-20251001 call, (3) stores the summary as a system message in chat_messages with metadata {"type": "rolling_summary"}, (4) returns the summary + last 10 messages as the conversation context for the agent. On subsequent calls, reuse the existing summary and only re-summarize when new messages push past the window. Update the build_context node in api/agent/graph.py to use this function.
```

---

#### 6C-2: User profile summary (Layer 2)

**Goal:** Generate a concise profile summary that gives the agent awareness of the user's data without loading everything.

**Files to modify:**
- `api/skills/memory.py` — add `build_profile_summary()` that queries products, engagements, org membership and returns a ~300 token summary
- `api/agent/system_prompt.py` — include the profile summary in Layer 2

**Verify:** Create several product analyses. Start a new chat. The agent should be able to say "You have 3 saved products: T-shirt, Water Bottle, Backpack" without the user telling it — confirming Layer 2 is loaded.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, Layer 2 description. Update api/skills/memory.py to add a build_profile_summary(user_id, access_token) function. It should: query get_all_products() for the user's products (just names + totals + dates, not line items), count active supplier engagements, check org membership via db/org_store.py, and compose a concise text summary like: "User has analyzed 3 products: T-shirt (12.4 kg CO₂e, 2024-01-15), Water Bottle (8.7 kg CO₂e, 2024-01-20), Backpack (23.1 kg CO₂e, 2024-02-01). 2 active supplier engagements. Member of Acme Corp (4 team members, 47 total products analyzed)." Update api/agent/system_prompt.py to call this and include it in the system prompt as Layer 2. Cache the result in-memory with a 5-minute TTL.
```

---

#### 6C-3: Semantic memory read/write

**Goal:** The agent can remember things across sessions and load them into context.

**Files to modify:**
- `api/agent/system_prompt.py` — load user + org memories into Layer 3
- `api/agent/graph.py` — after generating a response, add a post-processing step that evaluates whether anything is worth remembering
- `api/skills/memory.py` — add memory management (cap at 10 active user memories)

**Verify:** Tell the chat "I'm focused on reducing packaging emissions." Start a new chat session. The agent should reference this preference without being told again. Verify max 10 memories — the 11th should archive the oldest.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, semantic memory design. Update api/agent/system_prompt.py to load user memories (from db/memory_store.py) and org memories into Layer 3. Format as a bullet list: "User preferences: • Focused on reducing packaging emissions • Prefers metric tons". Update api/agent/graph.py to add a post-processing node after save_to_history called evaluate_memory. This node makes a short Claude claude-haiku-4-5-20251001 call: given the conversation turn, should anything be saved to user memory? If yes, write it via db/memory_store.py. Update api/skills/memory.py to enforce a cap of 10 active user memories — when writing the 11th, archive the oldest (set an archived_at timestamp).
```

---

#### 6C-4: Organization features

**Goal:** Users can create/join orgs. Org members see each other's data. Org memory is shared.

**Files to create/modify:**
- `api/routes/org.py` — endpoints for org CRUD and membership
- `frontend/app/settings/org/page.tsx` — minimal org management page
- Update RLS policies on `products` and `line_items` to allow org-wide visibility
- Update Analysis skill to support org-wide queries

**Verify:** Create two user accounts. User A creates an org and invites User B. User B joins. User B can now see User A's product analyses through the chat. Org memory written by User A appears in User B's system prompt.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, teams/multi-tenancy section. 

Backend: Create api/routes/org.py with endpoints: POST /api/orgs (create org), POST /api/orgs/{org_id}/members (add member by email), GET /api/orgs/mine (get user's org + members), DELETE /api/orgs/{org_id}/members/{user_id} (remove member). Update RLS policies on products and line_items: if a user belongs to an org, they can read all rows where user_id is any member of their org. Update api/skills/analysis.py to accept an optional scope parameter ("personal" or "org") — default to "org" when the user has an org.

Frontend: Create frontend/app/settings/org/page.tsx — simple page: show current org name + member list, "Create organization" button, "Add member" form (email input). Use shadcn Card, Table, Input, Button components.
```

---

### Phase 6D: Entry Points and Polish

#### 6D-1: Thread title auto-generation

**Goal:** Chat threads get readable titles automatically.

**Files to modify:**
- `api/routes/chat.py` — after the first user message in a thread, generate a title
- `db/chat_store.py` — add update_thread_title()

**Verify:** Start a new chat, send "I want to analyze emissions for my new backpack product." The thread title in the sidebar should update to something like "Backpack emissions analysis."

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Add auto-generated thread titles. In api/routes/chat.py, after the first user message is processed (POST /messages endpoint), check if the thread has a title. If not, generate one: make a short Claude claude-haiku-4-5-20251001 call with the user's first message, system prompt "Generate a 3-6 word title for this chat thread. Return only the title, nothing else." Update the thread title via db/chat_store.py. Return the new title in the API response so the frontend can update the sidebar without refetching.
```

---

#### 6D-2: Home page redesign with central chat bar

**Goal:** The home page becomes a chat-first experience.

**Files to modify:**
- `frontend/app/page.tsx` — redesign with central chat bar, prompt suggestions, module cards, recent threads

**Verify:** Open the home page. See a central chat input. See 4-6 prompt suggestion cards. See module cards below. See recent threads list. Typing in the chat bar or clicking a suggestion navigates to `/chat` with the message pre-filled.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, entry points section. Redesign frontend/app/page.tsx as a chat-first home page.

Layout (top to bottom): (1) App title + subtitle centered. (2) Large chat input bar centered (like ChatGPT's home page) — typing and pressing Enter navigates to /chat?message=<encoded_text> and auto-sends the message. (3) Grid of 6 prompt suggestion cards in 2 rows of 3: "Analyze a bill of materials", "Check my Scope 3 gaps", "Draft a supplier email", "What is Scope 3?", "Compare my product footprints", "Show my highest hotspots". Each card has a short subtitle and an icon. Clicking navigates to /chat with the prompt pre-filled. (4) Row of 4 module cards (BOM Analyzer, Gap Analyzer, Supplier Copilot, Advisor) — clicking goes to /chat and sends the module trigger message. (5) "Recent conversations" section showing last 5 threads from the API.

Use shadcn/ui. Clean, professional, centered layout with generous whitespace.
```

---

#### 6D-3: Global chat icon

**Goal:** An AI icon in the top-right corner of every page that opens a chat drawer.

**Files to create/modify:**
- `frontend/components/layout/GlobalChatIcon.tsx` — floating icon button
- `frontend/components/layout/ChatDrawer.tsx` — slide-out drawer with a compact chat interface
- Update the root layout to include GlobalChatIcon on all pages

**Verify:** Navigate to any page (analyzer, settings, etc.). See the AI icon in the top-right. Click it — a drawer slides in from the right with the chat. Send a message, get a response. Close the drawer. The icon is present on every page.

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md, entry points section. Add a global chat icon.

Create frontend/components/layout/GlobalChatIcon.tsx — a fixed-position circular button (bottom-right or top-right, 48px, with a sparkle/AI icon from lucide-react). On click, opens a ChatDrawer. Create frontend/components/layout/ChatDrawer.tsx — a shadcn Sheet (side="right", ~400px wide) containing a compact version of the chat: ChatThread + ChatInput, no sidebar, no module buttons (those are only on the full /chat page). The drawer loads the most recent thread or creates a new one. Add GlobalChatIcon to the root layout (frontend/app/layout.tsx) so it appears on every page. Don't show it on the /chat page itself (redundant).
```

---

#### 6D-4: Loading states and error handling

**Goal:** Polish the chat experience with proper loading indicators, streaming, error messages, and retry.

**Files to modify:**
- `frontend/components/chat/ChatMessage.tsx` — add streaming dots animation for in-progress responses
- `frontend/components/chat/ChatThread.tsx` — add error message bubbles with retry button
- `frontend/lib/chat-api.ts` — add SSE streaming support for the send message endpoint
- `api/routes/chat.py` — add SSE streaming endpoint for agent responses

**Verify:** Send a message — see animated dots while the agent thinks. If the API errors, see an error message in-chat with a "Retry" button. Click retry — the message re-sends. Agent responses stream in token-by-token (or chunk-by-chunk).

**Prompt:**
```
Read PLATFORM_CHAT_AGENT_PLAN.md. Polish the chat UX.

Backend: Add a streaming variant of the send message endpoint — POST /api/chat/threads/{thread_id}/messages/stream that returns an SSE stream. The agent graph runs normally, but the final LLM response is streamed via server-sent events. Use FastAPI's StreamingResponse with media_type="text/event-stream".

Frontend: Update frontend/lib/chat-api.ts to support SSE — add a sendMessageStream() function that returns an async iterator of text chunks. Update ChatMessage.tsx to support a "streaming" state with animated dots (three dots pulsing). Update ChatThread.tsx to handle errors: if sendMessage fails, show an error ChatMessage with red styling and a "Retry" button. Clicking retry re-sends the last user message. Add a subtle typing indicator when the assistant is responding.
```

---

## Order of Operations

```
6A-1 (DB migrations)
  → 6A-2 (DB CRUD layer)
    → 6A-3 (Analysis + Guidance skills)
    → 6A-4 (Engagement + Memory skills)
      → 6A-5 (Agent core + API endpoints)

6A-5 enables ↓

6B-1 (Basic chat UI)
  → 6B-2 (Module buttons + suggestions)
    → 6B-3 (Inline intake forms)
      → 6B-4 (Split layout + panels)
        → 6B-5 (BOM + Gap panels)
        → 6B-6 (Supplier panel + persistence)
      → 6B-7 (Thread history sidebar)

6B-1 enables ↓

6C-1 (Conversation summarization)
6C-2 (Profile summary — Layer 2)
6C-3 (Semantic memory)
6C-4 (Org features)

All of 6B + 6C enables ↓

6D-1 (Thread titles)
6D-2 (Home page redesign)
6D-3 (Global chat icon)
6D-4 (Loading states + streaming)
```

**Parallelism notes:**
- 6A-3 and 6A-4 can run in parallel (independent skills)
- 6B-5 and 6B-6 can run in parallel (independent panels)
- 6B-7 can start as soon as 6B-1 is done (independent of panels)
- All 6C steps can run in parallel (independent of each other, only need 6B-1)
- All 6D steps can run in parallel (independent polish tasks)

---

## Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Skills vs raw tools | 4 skills | Better LLM routing accuracy, encapsulates complexity, easier to extend |
| Context loading | Progressive disclosure (5 layers) | Keeps per-turn token cost low; only loads details when the skill needs them |
| Intake forms | Predefined templates | Deterministic, no risk of LLM hallucinating wrong fields, easier to validate |
| Panel state persistence | Database (active_panels table) | Survives page refresh, enables multi-device access later |
| Chat history | Full persistence in DB | Users can revisit old threads; enables cross-session memory |
| Conversation summarization | Rolling summary after 10 messages | Keeps context window manageable without losing important history |
| Org data visibility | Everyone sees everything | Simpler to build; role-based access can be added later |
| Semantic memory scope | User + org levels | Personal preferences stay personal; company context is shared |
| Entry points | Home chat bar + global icon | Chat-first UX; accessible from any page |

---

## Dependencies on Prior Phases

This plan assumes Phases 1–5 are complete:
- FastAPI backend is running (Phase 1)
- Supabase is set up with auth and RLS (Phase 3)
- Next.js frontend exists with auth (Phase 4)
- Existing modules (analyzer, advisor, gap analyzer, copilot) have working API endpoints

If any of these are incomplete, complete them first before starting Phase 6.
