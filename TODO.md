# Supply Chain War Room — Roadmap

> Living task list. Priorities ordered top-to-bottom within each tier.

## Tier 1 — Wire the Core Loop (make it feel alive)

- [x] **SSE live updates on frontend** — Broadcast event bus with heartbeats, publish_event() wired into all state-change points (risks, agents, simulations, ingestion). Frontend hook already consumes.
- [x] **Live ingestion → risk agent pipeline** — Automated triage runs after every ingestion cycle: re-scores suppliers, detects regional escalations, creates alerts, broadcasts via SSE. Optional Claude agent deep-analysis for high-risk signals.
- [x] **Human-in-the-loop approval gate** — PATCH endpoint with state machine validation, approve/reject buttons in AgentLog with glow effects on proposed decisions, SSE broadcast on status change.

## Tier 2 — Deepen the Intelligence

- [x] **Decision audit trail (full reasoning)** — AgentLog expands on click to show full reasoning, parsed parameters table, cost/time impact, affected orders, trigger event, reviewer notes, and timeline. Lazy-loads detail from API.
- [x] **Agent-to-agent handoff visibility** — Show in the UI when the orchestrator delegates to risk monitor → simulation → mitigation agents. Animated flow or timeline view of the agent pipeline.
- [x] **Scenario builder UI** — Let users compose custom disruption scenarios (pick affected routes/suppliers, set severity, duration) instead of only using presets. Wire to the Monte Carlo engine.

## Tier 3 — Portfolio Showstoppers

- [x] **Demo mode / guided walkthrough** — A "Demo" button that auto-plays a scenario end-to-end: triggers a disruption, risk feed lights up, agents deliberate in chat, simulation runs, mitigation gets proposed — all animated in real time. Killer for portfolio walkthroughs and interviews.
- [x] **Executive summary generation** — After a simulation completes, generate a one-page executive brief (PDF or styled HTML) summarizing the disruption, Monte Carlo results, agent recommendations, and estimated ROI of mitigation. Shows "boardroom-ready" output.
- [x] **Multi-scenario comparison** — Run 2-3 scenarios side-by-side and compare outcomes. Visualization showing overlapping cost/delay distributions.

## Tier 4 — Deepen Technical Impressiveness

- [x] **WebSocket upgrade** — Replace SSE with WebSockets for bidirectional real-time (shows you know the tradeoffs). Graceful fallback to SSE for environments that don't support WS.
- [x] **Agent memory / learning** — Agents reference past decisions to improve recommendations over time. Store learned patterns in a memory layer, surface "last time this happened, we..." context.
- [x] **Alerting rules engine** — Let users define custom alert thresholds (e.g. "notify me when any supplier reliability drops below 0.7") that trigger agent analysis automatically.

## Tier 5 — Ship & Present

- [ ] **Capture README screenshots/GIFs** — Take dashboard, simulation, comparison, executive summary, agent pipeline screenshots + demo mode GIF. See docs/PRESENTATION_PLAN.md for full shot list and capture sequence.
- [x] **Live deployment** — Docker Compose prod mode (nginx + built SPA), Railway config (backend + Postgres), Vercel config (frontend). See docs/PRESENTATION_PLAN.md.
- [ ] **Video walkthrough** — 2-minute narrated demo with TTS voiceover. Full script and production steps in docs/PRESENTATION_PLAN.md.

## Completed

- [x] Full backend: FastAPI, DB models, seed data, agent definitions
- [x] React command-center dashboard with dark theme
- [x] Monte Carlo simulation engine (NumPy, real math, deterministic seeds)
- [x] Simulation engine wired end-to-end (create → auto-run → results in one trip)
- [x] Agent chat interface (ChatPanel + `/api/v1/agents/chat` + Claude SDK)
- [x] Risk monitor agent with tools (query events, score suppliers, create alerts)
- [x] GDELT news + Open-Meteo weather live ingestion with relevance filtering
- [x] Docker Compose deployment with auto-seed entrypoint
- [x] CI pipeline + E2E tests + 460-line simulation engine test suite
