# Agent Instructions

All project rules live in **`Claude.md`** (project purpose, architecture and dependency rules, decision rules, eval invariants, coding conventions, and rules for AI-assisted implementation). Read it in full before making changes.

Product direction and the current feature roadmap live in **`PCF_PLATFORM_DESIGN.md`**.

Non-negotiables (details in Claude.md):
- Follow the current phase's implementation plan exactly; do not refactor outside its scope.
- Business logic modules (`calc/`, `factors/`, `parsing/`, `llm/`, `rag/`, `gap_analyzer/`, `copilot/`, `db/`) never import UI or route code.
- Never write credentials into source files; environment variables only.
- CI must pass: ruff + pytest + golden-file evals (backend), ESLint + `next build` (frontend).
