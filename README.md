# Supply Chain War Room  

**An enterprise-grade, multi-agent AI system for supply chain risk monitoring, simulation, and autonomous decision-making.**

Built with the Claude Agent SDK, this system demonstrates how agentic AI can continuously monitor a global supply chain, detect emerging risks, run Monte Carlo simulations of disruption scenarios, propose cost-optimized mitigation strategies, and execute decisions — all through a command-center dashboard with a conversational AI interface.

> This is literally what companies pay seven figures to Accenture to build.

---

## What It Does

- **Real-time Risk Monitoring** — AI agents continuously scan for supply chain disruptions: port closures, supplier delays, demand spikes, geopolitical events
- **Monte Carlo Simulation** — Run 10,000-iteration what-if scenarios ("What if the Suez Canal closes for 3 weeks?") with statistically valid results (p50/p90/p95/p99)
- **AI-Powered Strategy** — Agents generate mitigation plans with cost-benefit analysis, alternative supplier recommendations, and rerouting options
- **Autonomous Execution** — With human approval, agents reroute orders, trigger safety stock purchases, and update supplier status — all logged to an audit trail
- **Queryable Reasoning** — Ask "Why did you reroute order PO-2025-0042?" and get the full chain of agent reasoning
- **Command Center Dashboard** — Dark-themed war room UI with world map, risk feed, supplier health grid, and real-time agent decision stream

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                       │
│  GlobalMap │ RiskFeed │ Suppliers │ Orders │ Chat Panel  │
│  DemandChart │ AgentLog │ SimPanel │ StatusBar           │
└──────────────────────────────────────┬──────────────────┘
                                       │ SSE + HTTP
┌──────────────────────────────────────┴──────────────────┐
│                 Backend (FastAPI)                         │
│  REST API ──── Agent Bridge (Claude SDK) ──── SSE Stream │
│       │              │                                   │
│   Services      Orchestrator Agent                       │
│       │         ┌────┴────────────────────┐              │
│   PostgreSQL    │ Risk    │ Simulation    │              │
│   / SQLite      │ Monitor │ Agent         │              │
│                 │ Strategy│ Execution     │              │
│                 │ Agent   │ Agent         │              │
│                 └─────────┴───────────────┘              │
│                        │                                 │
│              Monte Carlo Engine (NumPy)                   │
└──────────────────────────────────────────────────────────┘
```

### Agent Hierarchy

| Agent | Role | Key Tools |
|-------|------|-----------|
| **Orchestrator** | Routes queries to specialists, chains multi-step workflows | `get_war_room_context`, `query_decision_log` |
| **Risk Monitor** | Detects and scores supply chain risks | `query_risk_events`, `score_suppliers`, `create_alert` |
| **Simulation** | Runs what-if Monte Carlo scenarios | `run_monte_carlo`, `list_preset_scenarios` |
| **Strategy** | Generates mitigation plans with cost analysis | `query_alternatives`, `generate_plan`, `cost_analysis` |
| **Execution** | Executes approved actions with full audit trail | `reroute_order`, `trigger_safety_stock`, `send_webhook` |

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/rhapsodic-legacy/supply-chain-warroom.git
cd supply-chain-warroom
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

docker-compose up
```

Open http://localhost:5173

### Option 2: Local Development

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python3 -m app.seed.generator    # Seed with synthetic data
python3 -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Try These Prompts

Once running, open the Chat Panel and try:

| Prompt | What Happens |
|--------|-------------|
| "What are the top risks right now?" | Risk Monitor scans active events, scores severity |
| "How reliable are our East Asia suppliers?" | Risk Monitor computes composite risk scores |
| "Simulate a 3-week Suez Canal closure" | Simulation Agent runs 10K Monte Carlo iterations |
| "What if our Shanghai supplier goes down for a month?" | Single-source failure simulation |
| "What should we do about the Rotterdam strike?" | Strategy Agent generates mitigation plan |
| "Run the demand shock scenario" | Tests resilience against 60% demand spike |
| "Execute the rerouting plan" | Execution Agent reroutes orders (after approval) |
| "Why was order PO-2025-0042 rerouted?" | Retrieves full decision chain from audit log |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Agents** | Claude Agent SDK (Anthropic), Claude Sonnet |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy async |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Shadcn/ui |
| **Simulation** | NumPy Monte Carlo engine (10K iterations < 0.2s) |
| **Charts** | Recharts, react-simple-maps |
| **Real-time** | Server-Sent Events (SSE) |
| **Database** | PostgreSQL (production) / SQLite (development) |
| **State** | Zustand + TanStack Query |

---

## Synthetic Data

The system ships with a deterministic synthetic data generator — no external APIs needed:

- **20 suppliers** across 5 regions (East Asia, South Asia, Europe, Americas)
- **25 products** across 4 categories (electronics, automotive, pharma, consumer goods)
- **36 shipping routes** covering major global trade lanes
- **300 orders** with realistic status distribution and delays
- **3,900 demand signals** with seasonality, trends, and anomalies
- **23 risk events** including 3 vivid, currently active scenarios

---

## How Simulations Work

The Monte Carlo engine models the supply chain as a directed weighted graph:

1. **Baseline** — Normal operations with stochastic lead times (log-normal distribution)
2. **Disruption** — Apply scenario (route closure, capacity reduction, demand spike)
3. **10,000 iterations** — Sample lead times, compute flow, track cost/delay/fill rate
4. **Statistical output** — p50, p90, p95, p99 distributions for all metrics
5. **Agent interpretation** — The AI analyzes results and recommends actions

The math is real NumPy computation — not LLM-generated numbers.

---

## Decision Audit Trail

Every agent action is logged to the `agent_decisions` table with:
- Which agent made the decision
- What triggered it (risk event, user request, simulation result)
- Full reasoning chain
- Confidence score
- Cost and time impact estimates
- Execution status and outcome

This makes every decision fully traceable and queryable.

---

## Deployment

### Frontend → Vercel

1. Import the repo at [vercel.com/new](https://vercel.com/new)
2. Set **Root Directory** to `frontend`
3. Add environment variable: `VITE_API_URL` = your Railway backend URL
4. Deploy

### Backend → Railway

1. Create a new project at [railway.app](https://railway.app)
2. Connect the GitHub repo
3. Set **Root Directory** to `backend`
4. Add environment variables: `ANTHROPIC_API_KEY`, `DATABASE_URL` (Railway Postgres addon), `FRONTEND_URL`
5. Deploy — the `railway.toml` handles the rest

---

## Testing

```bash
cd backend && source .venv/bin/activate
python3 -m pytest tests/ -v    # 56 tests
```

---

## Built With Claude Code

This project was built using [Claude Code](https://claude.ai/code) with:

- **Hierarchical CLAUDE.md files** — Root + backend + frontend + agents conventions
- **6 custom slash commands** — `/add-agent`, `/gen-scenario`, `/add-dashboard-widget`, `/run-simulation`, `/dev-log`, `/sync-types`
- **Automated hooks** — Auto-format on save (ruff for Python, prettier for TypeScript)
- **Parallel subagents** — Frontend and backend built simultaneously

See [docs/CLAUDE_CODE_SHOWCASE.md](docs/CLAUDE_CODE_SHOWCASE.md) for the full development workflow documentation.

---

## License

MIT
