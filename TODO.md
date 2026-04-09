# Supply Chain War Room — Roadmap

> Living task list. Priorities ordered top-to-bottom within each tier.

## Tier 1 — Wire the Core Loop (make it feel alive)

- [ ] **SSE live updates on frontend** — Backend SSE endpoint exists (`/api/v1/stream`) but nothing consumes it. Build a `useEventStream()` hook and wire it into RiskFeed, AgentLog, and the global status bar so events push to the dashboard in real time.
- [ ] **Live ingestion → risk agent pipeline** — GDELT news + Open-Meteo weather ingestion is built. Wire those live signals into the risk monitor agent so it auto-detects real-world disruptions, scores them, and raises alerts via SSE — closing the loop from data → agent → dashboard.
- [ ] **Human-in-the-loop approval gate** — Data model supports `proposed→approved→executed→rejected` statuses. Add a PATCH endpoint to transition decisions, and add approve/reject buttons in the AgentLog panel. Execution agent must pause and wait for user confirmation.

## Tier 2 — Deepen the Intelligence

- [ ] **Decision audit trail (full reasoning)** — AgentLog currently shows surface-level summaries. Expand to show full agent reasoning chain, tool calls, confidence breakdown, and cost-impact analysis on click. Make it feel like a real SOC analyst's investigation log.
- [ ] **Agent-to-agent handoff visibility** — Show in the UI when the orchestrator delegates to risk monitor → simulation → mitigation agents. Animated flow or timeline view of the agent pipeline.
- [ ] **Scenario builder UI** — Let users compose custom disruption scenarios (pick affected routes/suppliers, set severity, duration) instead of only using presets. Wire to the Monte Carlo engine.

## Tier 3 — Portfolio Showstoppers

- [ ] **Demo mode / guided walkthrough** — A "Demo" button that auto-plays a scenario end-to-end: triggers a disruption, risk feed lights up, agents deliberate in chat, simulation runs, mitigation gets proposed — all animated in real time. Killer for portfolio walkthroughs and interviews.
- [ ] **Executive summary generation** — After a simulation completes, generate a one-page executive brief (PDF or styled HTML) summarizing the disruption, Monte Carlo results, agent recommendations, and estimated ROI of mitigation. Shows "boardroom-ready" output.
- [ ] **Multi-scenario comparison** — Run 2-3 scenarios side-by-side and compare outcomes. Visualization showing overlapping cost/delay distributions.

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
