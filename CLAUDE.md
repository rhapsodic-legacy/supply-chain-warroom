# Supply Chain War Room

Real-time supply chain risk monitoring and simulation platform. AI agents analyse disruptions, predict cascading impacts, and recommend mitigations. Built with Claude Agent SDK to showcase agentic development workflows.

## Tech Stack
- Backend: Python 3.12, FastAPI, Claude Agent SDK, SQLAlchemy async, NumPy
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + Shadcn/ui + Recharts
- Database: PostgreSQL (Docker Compose) with SQLite fallback
- Real-time: Server-Sent Events (SSE)

## Monorepo Layout

| Directory   | Purpose                                        |
|-------------|------------------------------------------------|
| backend/    | FastAPI API server, database models, services  |
| frontend/   | React dashboard SPA                            |
| docs/       | Architecture docs, development log, showcase   |
| scripts/    | Hook scripts, utility scripts                  |

## How the Pieces Connect

1. **Data layer** generates synthetic supply chains (suppliers, routes, inventory)
2. **Agents** monitor supply chain state and respond to risk events via Claude Agent SDK
3. **Backend** exposes REST + SSE endpoints consumed by frontend and called by agent tools
4. **Frontend** renders a command-center dashboard with live status, risk scores, agent decisions, and a conversational chat interface

## Running the Project

```bash
# Full stack via Docker Compose
docker-compose up

# Or individually:
cd backend && python3 -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

## Development Commands

- Python: `python3` on macOS
- Backend tests: `cd backend && python3 -m pytest`
- Frontend tests: `cd frontend && npm test`
- Seed database: `cd backend && python3 -m app.seed.generator`
- Custom slash commands: `/add-agent`, `/gen-scenario`, `/add-dashboard-widget`, `/run-simulation`, `/dev-log`, `/sync-types`

## Conventions

- Python: ruff formatting (line length 100, double quotes)
- TypeScript: prettier defaults
- All models have id (UUID), created_at, updated_at columns
- Routers handle HTTP concerns only; business logic lives in services/
- Every dashboard widget handles loading, error, and empty states
- Commit messages: imperative mood, under 72 chars, body explains why
- Branch names: feature/short-description, fix/short-description

## Critical Rules

1. Never use real company names or data. All data is synthetic.
2. Agent models: Sonnet for all agents (balance of capability and cost).
3. Backend is source of truth for all types. Frontend types derived from backend schemas.
4. Execution agent requires explicit user approval before taking action.
5. Every agent tool invocation is logged to the decision audit trail.
6. Monte Carlo simulation uses real NumPy computation, not LLM-generated numbers.
