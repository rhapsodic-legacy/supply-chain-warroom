# Claude Code Showcase — Supply Chain War Room

This document explains how Claude Code's advanced features were used to build this project. Written for portfolio reviewers who want to understand the development workflow.

## Hierarchical CLAUDE.md Architecture

The project uses multiple CLAUDE.md files in a hierarchy:

```
CLAUDE.md (root)           Project overview, conventions, how pieces connect
  backend/CLAUDE.md        Python/FastAPI patterns, testing approach
  frontend/CLAUDE.md       React/TypeScript patterns, component conventions
```

**Why this matters:** When Claude Code works in a subdirectory, it reads both the root CLAUDE.md and the local one. The backend agent automatically knows Python conventions, while the frontend agent knows React patterns. Cross-cutting concerns (naming, testing philosophy, how components connect) stay consistent everywhere.

## Custom Slash Commands

Six project-specific commands automate repetitive scaffolding:

| Command | What it does |
|---------|-------------|
| `/add-agent` | Scaffolds agent definition, tools, tests, and registry entry |
| `/gen-scenario` | Generates a creative supply chain disruption scenario |
| `/add-dashboard-widget` | Scaffolds React component, hook, test, dashboard entry |
| `/run-simulation` | Triggers a simulation from the CLI |
| `/dev-log` | Appends a timestamped entry to the development log |
| `/sync-types` | Regenerates frontend TS types from backend Pydantic schemas |

Each command encodes the project's conventions so that scaffolded code is consistent from day one.

## Hooks

### Auto-Format on Save (PostToolUse)
Every time Claude Code writes or edits a file, a hook runs ruff (Python) or prettier (TypeScript) to ensure consistent formatting.

## Subagent Parallelism

For full-stack features, parallel subagents are used:
- Agent 1 builds the backend (FastAPI routers, services, database queries)
- Agent 2 builds the frontend (React components, hooks, TypeScript types)
- Agent 3 builds the simulation engine and agent tools

This mirrors how a real engineering team divides work, but happens in a single session.

## Plan Mode

Before writing any code, Claude Code's Plan mode was used to:
1. Design the complete architecture across three dimensions (agent system, data model, Claude Code infrastructure)
2. Make technology decisions with documented trade-offs
3. Define the implementation sequence
4. Identify critical files and dependencies

The plan was reviewed and approved before implementation began.
