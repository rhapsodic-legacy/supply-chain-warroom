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
