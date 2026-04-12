# Development Log — Supply Chain War Room

This log documents how Claude Code was used to build this project. Each entry records what was built, which Claude Code features were used, and lessons learned.

---

## 2026-04-02 — Project Foundation and Full Stack Build

**What was built:** Complete supply chain war room from scratch — backend (FastAPI + SQLAlchemy + Claude Agent SDK), frontend (React + Vite + Tailwind), simulation engine (NumPy Monte Carlo), synthetic data generator, and Claude Code development infrastructure.

**Files created:** 80+ files across backend, frontend, docs, and Claude Code configuration.

**Key components:**
- 10-table database schema (suppliers, products, routes, orders, demand, risks, agents, simulations)
- 5-agent hierarchy (Orchestrator → Risk Monitor, Simulation, Strategy, Execution)
- Monte Carlo simulation engine with 4 preset scenarios
- Synthetic data generator producing 4,400+ records of realistic supply chain data
- 8 dashboard panels (GlobalMap, RiskFeed, SupplierGrid, OrderTracker, DemandChart, AgentLog, SimPanel, ChatPanel)
- 6 custom slash commands for Claude Code workflow

**Claude Code techniques:**
- Hierarchical CLAUDE.md files (root + backend + frontend) for context-aware development
- Parallel subagent delegation: frontend and backend built simultaneously
- Custom slash commands: `/add-agent`, `/gen-scenario`, `/add-dashboard-widget`, `/run-simulation`, `/dev-log`, `/sync-types`
- Post-save hook for auto-formatting (ruff for Python, prettier for TypeScript)
- Plan mode for comprehensive architecture design before implementation

**Challenges:**
- SQLAlchemy model defaults (datetime.utcnow) don't apply during bulk SQL inserts — resolved by injecting timestamps in the seed generator
- Python version mismatch (system 3.9 vs required 3.12) — resolved by creating a venv with the correct Python

---

## 2026-04-11 14:30 — Agent Memory / Learning

**What was built:** Full agent memory and learning system. Agents now store lessons learned from past decisions and retrieve them to inform future recommendations. When facing a new disruption, agents surface "last time this happened…" context — improving over time as more decisions are recorded and evaluated.

**Key components:**
- `AgentMemory` database model with classification fields (category, region, risk type, severity) for structured similarity matching
- Memory service with relevance-scored retrieval — matches on category, region, risk type, and severity with weighted scoring
- Two new agent tools: `recall_similar_decisions` (search past lessons) and `record_lesson` (capture new learnings)
- Memory tools wired into the Orchestrator (recall + record) and Strategy agent (recall + record) with updated system prompts
- REST API: `GET /memories`, `GET /memories/stats`, `GET /memories/:id` — all under `/api/v1/agents/`
- 9 seed memories spanning historical lessons (Suez blockage, factory fires, demand spikes, geopolitical tensions) and current-scenario outcomes
- Frontend "Memory" tab in the agent panel with expandable detail cards, effectiveness progress bar, and outcome-colored badges
- 15 new backend tests (service unit tests + API endpoint tests) — all passing, 140 total suite green

**Files created:**
- `backend/app/models/agent_memory.py` — SQLAlchemy ORM model
- `backend/app/services/memory_service.py` — store, retrieve, match, stats
- `backend/app/agents/tools/memory_tools.py` — recall_similar_decisions, record_lesson
- `backend/app/schemas/memory.py` — Pydantic response schemas
- `backend/app/seed/agent_memories.py` — 9 realistic seed memories
- `backend/tests/test_agent_memory.py` — 15 tests
- `frontend/src/hooks/useMemories.ts` — React Query hooks
- `frontend/src/components/panels/AgentMemoryPanel.tsx` — dashboard panel

**Files modified:**
- `backend/app/models/__init__.py` — registered AgentMemory
- `backend/app/schemas/__init__.py` — registered memory schemas
- `backend/app/agents/orchestrator.py` — added memory tools + INSTITUTIONAL MEMORY prompt section
- `backend/app/agents/strategy_agent.py` — added memory tools + prompt section
- `backend/app/routers/agents.py` — 3 new memory endpoints
- `backend/app/seed/generator.py` — memory seed generation + insertion
- `backend/tests/conftest.py` — memory seed data in test fixtures
- `frontend/src/types/api.ts` — AgentMemory, AgentMemoryBrief, AgentMemoryStats types
- `frontend/src/components/layout/WarRoomShell.tsx` — added Memory tab
- `TODO.md` — marked task complete

**Claude Code techniques:**
- Explore subagent for deep codebase analysis before implementation — mapped all agent, model, service, and tool patterns in one pass
- Parallel tool calls throughout: reading multiple files simultaneously, creating independent files in batch
- TodoWrite for structured task tracking across 8 implementation steps
- `/dev-log` skill for automated log entry generation

**Challenges:**
- Memory similarity matching without vector embeddings — resolved with structured field matching using weighted scoring (category 4x, region/risk_type 2x, severity 1x). Simple, fast, no extra dependencies, and interpretable
- System Python (3.14) didn't have pytest installed — used the project's `.venv/bin/python` (3.13) which had all dependencies

---

## 2026-04-11 15:15 — Alerting Rules Engine

**What was built:** User-defined alerting rules engine. Users create threshold-based rules (e.g. "notify me when any supplier reliability drops below 0.7") that are evaluated after every ingestion cycle. When a rule fires, the system creates a risk alert, broadcasts it via SSE, and optionally triggers agent analysis — closing the loop from user-defined policy to automated response.

**Key components:**
- `AlertRule` database model with metric, operator, threshold, optional scope filters (region, supplier, severity), cooldown tracking, and agent-trigger toggle
- 5 metric evaluators: `supplier_reliability`, `risk_event_count`, `order_delay_days`, `composite_risk_score`, `regional_risk_density`
- Evaluation engine with cooldown enforcement — rules won't re-fire within their cooldown window
- Rule evaluation wired into the ingestion scheduler (`_run_loop`), executing after every triage cycle
- Full CRUD REST API: list, create, get, update, delete, toggle enable/disable, manual evaluate
- 5 seed rules (reliability < 0.7, critical events > 3, regional density, order delay > 7d, composite risk > 0.6)
- Frontend panel with inline rule creation form, enable/disable toggle, delete, manual "Evaluate" button, expandable detail
- Panel placed in Row 2 alongside Risk Feed and Supplier Grid
- 21 new backend tests (8 CRUD, 6 evaluation, 7 API endpoints) — all passing, 161 total suite

**Files created:**
- `backend/app/models/alert_rule.py` — SQLAlchemy ORM model
- `backend/app/services/alert_rule_service.py` — CRUD + evaluation engine
- `backend/app/routers/alert_rules.py` — FastAPI router
- `backend/app/schemas/alert_rule.py` — Pydantic request/response schemas
- `backend/app/seed/alert_rules.py` — 5 default rules
- `backend/tests/test_alert_rules.py` — 21 tests
- `frontend/src/hooks/useAlertRules.ts` — React Query hooks (CRUD + evaluate)
- `frontend/src/components/panels/AlertRulesPanel.tsx` — dashboard panel with create form

**Files modified:**
- `backend/app/models/__init__.py` — registered AlertRule
- `backend/app/schemas/__init__.py` — registered alert rule schemas
- `backend/app/main.py` — registered alert_rules router
- `backend/app/ingestion/scheduler.py` — wired `evaluate_all_rules` into ingestion loop
- `backend/app/seed/generator.py` — alert rule seed generation + insertion + table delete order
- `backend/tests/conftest.py` — alert rule seed data in test fixtures
- `frontend/src/types/api.ts` — AlertRule, AlertRuleBrief, AlertRuleCreate types
- `frontend/src/components/layout/WarRoomShell.tsx` — added AlertRulesPanel to Row 2
- `TODO.md` — marked Tier 4 complete

**Claude Code techniques:**
- TodoWrite for 7-step task tracking across model → service → API → pipeline → frontend → tests → docs
- Parallel file reads to map codebase patterns (risk_analysis, scheduler, risk_service, supplier model) in one pass
- `/dev-log` skill for automated log entry

**Challenges:**
- FastAPI trailing-slash redirects caused 307 responses in API tests — resolved by using trailing slashes in test URLs and `params=` for query parameters instead of inline `?key=val`
- Composite risk score evaluation needed to replicate the formula from `risk_analysis._score_suppliers` to avoid a circular import — kept it self-contained in the evaluator
