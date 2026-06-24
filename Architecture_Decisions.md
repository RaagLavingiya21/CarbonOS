# Architecture Decisions: Why We Chose What We Chose

This document explains every architectural decision in the Product Carbon Footprint Analyzer's production stack, the alternatives we rejected, and the trade-offs we accepted. Written so you can articulate any decision in an interview.

---

## The Foundational Decision: Why Separate Frontend and Backend?

**What we're doing:** Two independent applications. A Python API server (FastAPI) and a JavaScript frontend (Next.js). They communicate over HTTP.

**The alternative:** Keep everything in one application (like Streamlit does — it's your UI, your server, and your business logic all in one Python process).

**Why we're separating them:**

The core reason is **independent scaling and deployment**. Your LLM calls are expensive and slow (2-8 seconds). Your frontend is cheap and fast (static HTML/JS). In a monolith, a user waiting for an LLM response ties up a server process that could be serving other users' UI requests. When they're separate, you can run 2 backend instances handling LLM calls and 0 frontend servers (because Vercel serves it from a CDN).

The second reason is **team simulation**. In a real company, the frontend and backend are worked on by different people, deployed on different schedules, and tested independently. A PM building a product this way signals "I understand how engineering teams actually work." A Streamlit monolith signals "I built this alone and didn't think about anyone else touching it."

The third reason is **replaceability**. If you later want a mobile app, a Slack bot, or a partner API integration, your backend doesn't change — you just add another client that calls the same endpoints. If everything is in Streamlit, you'd have to rewrite from scratch.

**The trade-off you're accepting:** More complexity in development. Two repos (or two directories), two deployment pipelines, CORS configuration, API contracts to maintain. For a solo builder, this is more overhead. You're accepting that overhead because the signal it sends and the architectural correctness outweigh the convenience of a monolith.

**When you'd choose differently:** If this were a pure internal tool for 3 people and would never be shown externally, Streamlit is fine. The separation matters because this is a portfolio piece that needs to demonstrate production thinking.

---

## Backend: Why FastAPI Over Flask, Django, or Express

**What we're choosing:** FastAPI (Python).

**What we rejected and why:**

**Flask** — Flask is the most popular Python web framework, and it would work. But Flask is synchronous by default. Your LLM calls to Anthropic's API are I/O-bound (you're waiting for a network response). In Flask, while one request waits for Claude to respond, that worker thread is blocked and can't serve other requests. FastAPI is async-native — it uses `async/await`, so while one request waits for an LLM response, the same process can handle other requests. For an AI application where every request involves a 2-8 second LLM call, this matters enormously.

FastAPI also generates OpenAPI documentation automatically from your type hints. When you define an endpoint like `async def analyze_bom(request: BOMRequest) -> AnalysisResponse`, FastAPI creates interactive API docs at `/docs`. This is both a development tool (you can test endpoints from a browser) and a portfolio artifact (it shows your API is well-defined and documented).

**Django** — Django is a "batteries-included" framework designed for content-heavy web applications (blogs, e-commerce, CMS). It comes with an ORM, admin panel, template engine, and a lot of machinery you don't need. Your backend is an API server that mostly orchestrates LLM calls and database reads. Django's overhead doesn't buy you anything, and it adds complexity. It's like using a semi truck to deliver a letter.

**Express.js (Node.js backend)** — This would mean rewriting your entire backend in JavaScript. Your LLM logic, RAG pipeline, LangGraph agents, and MCP server are all Python. LangGraph is a Python library. The AI/ML ecosystem is Python-first. Rewriting to Express would mean losing access to LangGraph, LangChain, ChromaDB's Python client, and sentence-transformers. There's no benefit, only cost.

**The key insight:** Your backend language should be Python because that's where the AI ecosystem lives. FastAPI is the best Python web framework for I/O-heavy API servers. This isn't a preference — it's the technically correct choice for your workload.

**The trade-off:** FastAPI's async model is slightly harder to debug than Flask's synchronous model. Stack traces can be more confusing with async code. You're accepting that because the performance characteristics matter for an AI application.

---

## Frontend: Why Next.js Over React SPA, Vue, Svelte, or Streamlit

**What we're choosing:** Next.js (React framework), deployed on Vercel.

### Why Not Keep Streamlit

Streamlit re-runs your entire Python script from top to bottom on every user interaction. Click a button? The whole script re-executes. This means:
- State management is hacky (`st.session_state` is a global dict)
- You can't have proper routing (Streamlit "pages" are separate Python files, not URL routes)
- You can't control the layout beyond Streamlit's column/container primitives
- Loading states, animations, and responsive design are impossible or extremely limited
- Every interaction hits your Python server, even for purely client-side UI changes

More importantly: **everyone in the industry knows Streamlit is for prototypes.** It's not a matter of whether Streamlit *can* run in production (it technically can). It's that choosing it signals "I didn't graduate past the prototype stage." This is about perception as much as technical merit.

### Why Next.js Specifically, Not Plain React (Create React App / Vite)

A plain React app is a Single Page Application (SPA) — it's purely client-side JavaScript. The browser downloads a blank HTML page, then JavaScript renders everything. This has three problems:

1. **No server-side rendering (SSR).** The first page load is slow because the browser has to download, parse, and execute all the JavaScript before showing anything. Next.js renders the initial HTML on the server, so users see content immediately.

2. **No API routes.** A plain React app needs a completely separate backend for any server-side logic. Next.js has API routes built in — you can put lightweight server logic (auth checks, Supabase queries, caching) in the same project. Your heavy LLM work still goes to FastAPI, but simple data fetching can stay in Next.js.

3. **No file-based routing.** In plain React, you manually configure routes with React Router. In Next.js, you create a file at `app/analyzer/page.tsx` and it becomes the `/analyzer` route. Less boilerplate, less room for error.

4. **Vercel integration.** Next.js is made by Vercel. Deploying to Vercel is literally `git push` — it detects Next.js, builds it, deploys it, gives you a URL, and creates preview deployments for every PR branch. No Docker, no CI configuration, no infrastructure management. With your Vercel Pro account, you also get analytics, speed insights, and custom domains.

### Why Not Vue or Svelte

Both are good frameworks. Vue is popular in Asia and in some enterprise contexts. Svelte is elegant and has less boilerplate. But: React has the largest ecosystem, the most component libraries, and the most community support. Claude Code has trained on far more React code than Vue or Svelte, so the code it generates will be better. And if a GridCARE engineer looks at your frontend, React is what they expect. It's the default for a reason.

**The trade-off:** Next.js has a learning curve. The app router (introduced in Next.js 13) has concepts like Server Components vs. Client Components that can be confusing. React's state management (useState, useEffect, context) is more complex than Streamlit's `st.session_state`. You're accepting that complexity because the result looks and behaves like a real product.

---

## Database: Why Supabase Postgres Over Firebase, PlanetScale, Neon, or SQLite

**What we're choosing:** Supabase (which is hosted PostgreSQL + Auth + APIs).

### Why Not Keep SQLite

SQLite is an embedded database — it's a single file on disk. This means:
- **No concurrent writes.** If two users submit analyses simultaneously, one blocks the other. In production, this causes timeouts.
- **No network access.** Your frontend (on Vercel) and backend (on Railway/Render) would need to be on the same machine to access the same SQLite file. That breaks the frontend/backend separation.
- **No migrations.** When you change your schema (add a column, rename a table), there's no built-in migration system. You're manually writing ALTER TABLE statements and hoping you remember to run them.
- **No backups.** If the server dies, your data dies with it.

SQLite is perfect for embedded applications (mobile apps, desktop apps, IoT devices) and for development/testing. It's not appropriate for a web application with multiple users.

### Why Supabase Over Firebase

Firebase (Google) is a NoSQL document database (Firestore). Your data is relational — products have line items, suppliers have engagement records, analyses have emission factors. Relational data belongs in a relational database. Trying to model `product -> line_items -> emission_factors` in Firestore means either deeply nested documents (which become unwieldy) or multiple collections with manual joins (which defeats the purpose of a database).

Firebase also locks you into Google's ecosystem. Supabase is built on Postgres, which is the most widely-used relational database in the world. If you ever move off Supabase, your data and queries work on any Postgres host. If you move off Firebase, you rewrite everything.

Supabase also gives you:
- **Row-Level Security (RLS):** Database-level rules that say "user A can only read rows where `user_id = A`." This is multi-tenancy at the database level, not the application level. You don't have to remember to add `WHERE user_id = ?` to every query — the database enforces it.
- **Auth built in:** Email/password, OAuth (Google, GitHub), magic links. No separate auth service needed.
- **PostgREST API:** Supabase auto-generates REST APIs from your database tables. For simple CRUD operations, your Next.js frontend can talk to Supabase directly without going through FastAPI.
- **pgvector extension:** You can store vector embeddings directly in Postgres. This could eventually replace ChromaDB, giving you one database instead of two.

### Why Supabase Over PlanetScale or Neon

PlanetScale is MySQL-based (not Postgres) and recently removed their free tier. Neon is Postgres-based and is a solid alternative — but it's just a database. Supabase gives you the database PLUS auth, storage, and auto-generated APIs. For a solo builder, fewer services to manage means fewer things to break.

**The trade-off:** Supabase is a managed service. You're depending on a third party for your database. If Supabase has an outage, your app is down. You're also paying for it (though your Pro account covers this). The alternative would be self-hosting Postgres on a VPS, which gives you more control but dramatically more operational burden. For a portfolio project, managed services are the right call — you're demonstrating product thinking, not sysadmin skills.

---

## Backend Hosting: Why Railway/Render Over AWS, GCP, Fly.io, or Heroku

**What we're choosing:** Railway or Render for the FastAPI backend.

### Why Not Vercel for the Backend Too

Vercel is optimized for frontend frameworks. It runs serverless functions (Lambda under the hood) with a 30-second timeout on the Pro plan. Your LLM calls can take 10+ seconds, and LangGraph agent runs with multiple steps could easily exceed 30 seconds. Vercel's serverless model also means each request starts a new function instance — there's no persistent process to hold WebSocket connections for streaming agent responses. Your Python backend needs a long-running process, not serverless functions.

### Why Not AWS or GCP Directly

AWS (EC2, ECS, Lambda) and GCP (Cloud Run, GCE) give you maximum control and scalability. But they also require you to manage: Docker images, container registries, load balancers, VPCs, IAM roles, SSL certificates, auto-scaling policies, and CloudWatch/Cloud Monitoring dashboards. For a startup PM's portfolio project, this is operational overhead that adds zero product value. You'd spend more time on infrastructure than on your actual AI product.

A GridCARE interviewer won't be more impressed by "I managed an ECS cluster" than "I deployed on Railway." They will be impressed by your agent architecture, evals, and observability.

### Why Railway or Render

Both are "Platform as a Service" — you point them at a GitHub repo with a Dockerfile (or even just a `requirements.txt`), and they build, deploy, and host it. Auto-scaling, SSL, logging, and health checks are included. Deployment is `git push`. They're what startups actually use before they're big enough to justify AWS complexity.

Railway vs. Render specifically: Railway has a slightly better developer experience and supports WebSockets natively (important for streaming LangGraph agent responses to the frontend). Render has a more generous free tier. Either works.

**The trade-off:** Less control than AWS. If you need custom networking, GPU instances, or complex multi-region deployment, PaaS platforms won't cut it. For your use case, you don't need any of that.

---

## AI Framework: Why LangGraph Over CrewAI, AutoGen, or Raw Code

**What we're choosing:** LangGraph for agent orchestration.

### Why Not Keep the Current Raw Python Implementation

Your current code works. The Gap Analyzer plans, executes tools, and checkpoints. But the orchestration logic is tangled with Streamlit UI code, state lives in `st.session_state` (which dies when the browser tab closes), and there's no way to replay, debug, or observe agent runs after the fact.

LangGraph gives you:
- **State as a first-class concept.** Your agent's state is a typed object (TypedDict or Pydantic model), not a dict stuffed into session storage. You can serialize, inspect, and restore it.
- **Checkpointing.** Every step of the agent run is saved. If the process crashes, you resume from the last checkpoint. If a user closes their browser and comes back tomorrow, their analysis is still there.
- **Streaming.** LangGraph streams intermediate state updates to the client. The user sees "Planning... -> Analyzing emissions... -> Matching factors..." in real time, not a spinner for 30 seconds.
- **Human-in-the-loop built in.** `interrupt_before` pauses the graph at a specific node and waits for human input. This is exactly what your BOM review and emission factor review checkpoints need — but implemented as a framework primitive, not custom Streamlit hacks.
- **LangSmith integration.** Every LangGraph run automatically produces traces in LangSmith. No custom logging code needed.

### Why Not CrewAI

CrewAI is designed for multi-agent conversations where each agent has a "role" (researcher, writer, critic) and they talk to each other. Your product isn't that — it's a workflow with deterministic steps, conditional branching, and human checkpoints. Shoehorning that into CrewAI's role-based model would be unnatural.

CrewAI also abstracts away too much. You don't control the execution graph — CrewAI decides how agents interact. In a production application where you need predictable behavior (always check emissions before calculating, always pause for human review before saving), you need explicit control over the execution order. LangGraph gives you that with its graph definition.

### Why Not AutoGen (Microsoft)

AutoGen is focused on multi-agent conversations and code execution. Its primary use case is agents that write and run code to solve problems. Your product doesn't do that — it routes data through a defined workflow. AutoGen would add complexity without matching your use case.

### Why Not Just Write Your Own Orchestration

You could build a state machine in Python with a dict and some if/else logic. That's essentially what you have now. The problem is: you'd also need to build checkpointing, streaming, observability, error recovery, and human-in-the-loop interrupts. LangGraph has all of this tested and maintained. Writing your own version would take weeks and produce something less reliable. Using a framework when the framework fits your problem isn't laziness — it's engineering judgment.

**The trade-off:** LangGraph is a dependency. If LangChain (the company) changes direction or abandons it, you're affected. Your code is coupled to their API. The migration cost to something else would be real. You're accepting that because LangGraph is the market leader with active development and enterprise adoption — the risk of abandonment is low, and the benefit of not reinventing orchestration primitives is high.

---

## Observability: Why LangSmith Over Langfuse, Arize, or Custom Logger

**What we're choosing:** LangSmith for tracing and evals.

**What you have now:** A custom SQLite logger that records every LLM call with tokens, latency, errors, and RAG usage. This is good thinking — you built observability from the start. But it's limited.

### Why LangSmith

The pragmatic reason: you're already using LangGraph. LangSmith is made by the same company and integrates automatically. Every LangGraph run produces a trace in LangSmith with zero additional code — you just set the `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` environment variables. Building a custom integration with Langfuse or Arize for LangGraph traces would be additional work for no additional benefit.

The technical reason: LangSmith gives you things your custom logger doesn't:
- **Nested traces.** You see the full tree: agent run -> planner node -> LLM call -> tool call -> LLM call. Your logger only captures individual LLM calls, not the structure between them.
- **Eval datasets.** You can save production inputs as test cases and run evals against them. Your logger would need significant additional code to support this.
- **Comparison views.** Run the same input against two different prompts and compare outputs side by side. Essential for prompt iteration.
- **Feedback collection.** Users can rate outputs (thumbs up/down), and that feedback is linked to the specific trace. This closes the loop between "users are unhappy" and "here's the exact run that went wrong."

### Why Not Langfuse

Langfuse is open-source and self-hosted, which is great for companies that can't send data to a third party. You're not in that situation. Langfuse also requires you to manually instrument your code with their SDK — it doesn't auto-trace LangGraph runs. More work for a smaller feature set.

### Why Not Arize

Arize is strongest when you have both traditional ML models and LLM applications and need one platform for both. You only have LLM applications. Arize's drift detection and embedding analysis are powerful but unnecessary for your use case. It's also more expensive and enterprise-oriented.

### What to Keep From Your Current Logger

Your custom logger captures audit-specific data (which user ran which analysis, when, on what product). LangSmith traces are about debugging and optimization. Keep your audit logging for compliance/business purposes, but use LangSmith for observability. They serve different purposes.

**The trade-off:** LangSmith is paid beyond the free tier (though the free tier is generous). You're also sending your LLM inputs/outputs to LangChain's servers, which could be a concern for sensitive data. For a portfolio project, neither of these matters.

---

## UI Components: Why shadcn/ui

shadcn/ui is a collection of React components built on Radix UI primitives, styled with Tailwind CSS. Unlike Material UI or Chakra UI, shadcn/ui components are copied into your project — not installed as a dependency. You own the code, can customize everything, and there's no version lock-in.

More importantly: shadcn/ui is the current industry default for Next.js applications. It's what Claude Code will generate the highest-quality components with, because it's heavily represented in training data. And it produces clean, professional-looking UIs without design skill.

---

## The Big Picture: Why This Specific Architecture

The architecture follows a principle: **every choice should have a clear, defensible answer.**

| Decision | Interview Answer |
|----------|-----------------|
| "Why separate frontend/backend?" | "Independent scaling — LLM calls are slow and expensive, UI serving is cheap. Also enables mobile/API clients later." |
| "Why FastAPI?" | "Async-native for I/O-bound LLM workloads. Auto-generated API docs. The Python AI ecosystem lives here." |
| "Why Next.js?" | "SSR for fast initial load, file-based routing, Vercel deployment pipeline. Industry standard React framework." |
| "Why Supabase?" | "Postgres gives me relational integrity for hierarchical product data. RLS gives me multi-tenancy at the database level. Auth is built in." |
| "Why LangGraph?" | "I need explicit state management, checkpointing for long-running workflows, and human-in-the-loop interrupts. CrewAI doesn't give me that control." |
| "Why LangSmith?" | "Auto-traces LangGraph runs. Eval datasets from production traffic. I use it to catch regressions before users notice." |
| "Why Railway?" | "Startup-appropriate PaaS. I don't need AWS complexity for this workload, and I'd rather spend time on the product than on infrastructure." |

Notice that every answer is about **fit for the problem**, not about the technology being "best" in the abstract. That's what production thinking sounds like.

---

## Target Architecture

```
+---------------------------------------------+
|  Next.js Frontend (Vercel)                   |
|  - shadcn/ui components                      |
|  - Supabase Auth (client-side)               |
|  - Dashboard, Analyzer, Advisor, Copilot     |
+----------------------+-----------------------+
                       | API calls
+----------------------v-----------------------+
|  FastAPI Backend (Railway or Render)          |
|  - LangGraph agents (Gap Analyzer, Copilot)  |
|  - RAG pipeline (ChromaDB or pgvector)        |
|  - MCP server                                 |
|  - LangSmith tracing on every call            |
+------+-------------------+-------------------+
       |                   |
+------v------+     +------v------+
| Supabase    |     | LangSmith   |
| - Postgres  |     | - Traces    |
| - Auth      |     | - Evals     |
| - RLS       |     | - Cost      |
+-------------+     +-------------+
```
