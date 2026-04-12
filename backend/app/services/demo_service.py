"""Demo mode orchestrator — sequences real API calls for a guided walkthrough.

Runs the full supply-chain war room demo end-to-end:
  1. Injects a critical risk event (Suez Canal closure)
  2. Runs automated risk triage
  3. Launches a Monte Carlo simulation
  4. Triggers the agent chat pipeline (orchestrator → specialists)
  5. Publishes demo_step SSE events so the frontend overlay tracks progress

Agent fallback hierarchy:
  1. Claude API (ANTHROPIC_API_KEY) — full orchestrator with specialist handoffs
  2. Local Gemma 4 2B via Ollama — generates reasoning locally, no cloud needed
  3. Mock data — hardcoded realistic responses as last resort
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentDecision, AgentHandoff
from app.routers.stream import publish_event
from app.schemas import RiskEventCreate, SimulationCreate
from app.services import risk_service, simulation_service
from app.services.llm_utils import ollama_available, ollama_generate, resolve_llm_tier
from app.services.risk_analysis import run_triage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level state for active demos
# ---------------------------------------------------------------------------

_active_demo: dict[str, asyncio.Event] = {}  # demo_id → cancel event
_demo_lock = asyncio.Lock()

DEMO_STEPS = [
    "start",
    "risk_created",
    "triage_complete",
    "simulation_running",
    "simulation_complete",
    "agents_deliberating",
    "mitigation_proposed",
    "approval_gate",
    "complete",
]


async def _publish_step(step: str, panel: str | None = None, **extra: object) -> None:
    """Publish a demo_step SSE event."""
    await publish_event(
        "demo_step",
        {
            "step": step,
            "panel": panel,
            "step_index": DEMO_STEPS.index(step) if step in DEMO_STEPS else -1,
            "total_steps": len(DEMO_STEPS),
            **extra,
        },
    )


async def _is_cancelled(demo_id: str) -> bool:
    """Check whether the current demo run has been cancelled."""
    ev = _active_demo.get(demo_id)
    return ev is not None and ev.is_set()


# ---------------------------------------------------------------------------
# Agent tier resolution
# ---------------------------------------------------------------------------


async def _resolve_agent_tier() -> str:
    """Determine which agent backend to use: claude → gemma → mock."""
    tier = await resolve_llm_tier()
    return "mock" if tier == "template" else tier


# Prompts for Gemma agent simulation
_GEMMA_AGENT_PROMPTS: dict[str, str] = {
    "risk_monitor": (
        "You are a supply chain risk analyst. A vessel collision has blocked the Suez Canal "
        "for an estimated 7-14 days. 40% of Asia-Europe container traffic is affected. "
        "Provide a brief risk assessment: how many suppliers are at elevated risk, "
        "which routes are blocked, and estimated revenue at risk per day. "
        "Be specific with numbers. Keep your response under 100 words."
    ),
    "simulation": (
        "You are a supply chain simulation analyst. A Suez Canal closure has been modeled "
        "with 10,000 Monte Carlo iterations over 90 days. Summarize the key findings: "
        "percentage cost increase, P95 delay in days, and fill rate without mitigation. "
        "Be specific with numbers. Keep your response under 100 words."
    ),
    "strategy": (
        "You are a supply chain strategist. Given a Suez Canal closure causing $2M+/day "
        "revenue risk, propose a three-pronged mitigation: (1) emergency air freight, "
        "(2) dual-sourcing, (3) safety stock pre-positioning. Include approximate costs "
        "for each and total. Keep your response under 100 words."
    ),
}

# Fallback mock responses if no model is available
_MOCK_RESPONSES: dict[str, str] = {
    "risk_monitor": (
        "Risk assessment: 12 suppliers at elevated risk. "
        "3 critical routes through Suez now blocked. "
        "Estimated $2.4M/day revenue at risk."
    ),
    "simulation": (
        "Monte Carlo analysis shows 23% cost increase over 90 days. "
        "P95 delay: 18 days. Fill rate drops to 71% without mitigation."
    ),
    "strategy": (
        "Recommended: Activate air freight for critical components ($340K), "
        "dual-source 4 single-source suppliers ($180K setup), "
        "pre-position 2 weeks safety stock ($520K). Total: $1.04M vs $2.4M/day risk."
    ),
}


async def _run_local_agent_pipeline(
    db: AsyncSession,
    risk_event_id: str,
    created: dict[str, list[str]],
    use_gemma: bool = False,
) -> None:
    """Simulate the agent handoff pipeline using Gemma or mock data.

    Creates real AgentHandoff and AgentDecision records in the DB and
    broadcasts SSE events identical to the Claude orchestrator path.
    """
    session_id = str(uuid.uuid4())
    agent_source = "gemma" if use_gemma else "mock"

    for seq, agent in enumerate(["risk_monitor", "simulation", "strategy"]):
        # Start handoff
        handoff = AgentHandoff(
            session_id=session_id,
            sequence=seq,
            from_agent="orchestrator",
            to_agent=agent,
            query=f"Analyze Suez Canal closure impact — {agent} perspective",
            status="running",
        )
        db.add(handoff)
        await db.flush()
        created["handoff_ids"].append(handoff.id)

        await publish_event(
            "agent_handoff",
            {
                "handoff_id": handoff.id,
                "session_id": session_id,
                "sequence": seq,
                "from_agent": "orchestrator",
                "to_agent": agent,
                "query": handoff.query,
                "status": "running",
                "source": agent_source,
            },
        )

        # Generate response
        start = asyncio.get_event_loop().time()
        if use_gemma:
            try:
                summary = await ollama_generate(_GEMMA_AGENT_PROMPTS[agent])
            except Exception:
                logger.warning("Gemma generation failed for %s — using mock", agent)
                summary = _MOCK_RESPONSES[agent]
        else:
            await asyncio.sleep(2.0)  # Simulate thinking time for mocks
            summary = _MOCK_RESPONSES[agent]
        elapsed_ms = int((asyncio.get_event_loop().time() - start) * 1000)

        # Complete handoff
        handoff.status = "completed"
        handoff.completed_at = datetime.utcnow()
        handoff.duration_ms = elapsed_ms
        handoff.result_summary = summary[:300]
        await db.flush()

        await publish_event(
            "agent_handoff",
            {
                "handoff_id": handoff.id,
                "session_id": session_id,
                "sequence": seq,
                "from_agent": "orchestrator",
                "to_agent": agent,
                "status": "completed",
                "duration_ms": elapsed_ms,
                "source": agent_source,
            },
        )

    # Generate mitigation reasoning
    if use_gemma:
        try:
            reasoning = await ollama_generate(
                "You are a supply chain strategist writing a decision justification. "
                "The Suez Canal is blocked for ~10 days, disrupting 40% of Asia-Europe traffic. "
                "A Monte Carlo simulation projects 23% cost increase and fill rate drop to 71%. "
                "Justify a three-pronged mitigation plan (air freight, dual-sourcing, safety stock) "
                "totaling ~$1M against $2.4M/day revenue risk. Write 2-3 concise paragraphs.",
                max_tokens=500,
            )
        except Exception:
            logger.warning("Gemma reasoning generation failed — using mock")
            reasoning = None
    else:
        reasoning = None

    if not reasoning:
        reasoning = (
            "With the Suez Canal blocked for an estimated 10 days, "
            "40% of Asia-Europe container traffic is disrupted. "
            "Monte Carlo analysis projects a 23% cost increase and fill rate "
            "drop to 71% without intervention. The proposed three-pronged "
            "mitigation costs $1.04M but protects against $2.4M/day in "
            "potential losses. Air freight handles immediate critical needs, "
            "dual-sourcing reduces single-point-of-failure risk, and safety "
            "stock buffers against extended closure scenarios."
        )

    # Create proposed mitigation decision
    decision = AgentDecision(
        agent_type="strategy",
        decision_type="mitigation_plan",
        decision_summary=(
            "Activate emergency air freight corridor for critical electronics "
            "components + dual-source top 4 single-source suppliers + "
            "pre-position 2-week safety stock at Rotterdam hub"
        ),
        reasoning=reasoning,
        confidence_score=0.87,
        status="proposed",
        cost_impact=-1_040_000.0,
        time_impact_days=-5,
        affected_orders=8,
        parameters=json.dumps(
            {
                "air_freight_cost": 340_000,
                "dual_source_setup": 180_000,
                "safety_stock_cost": 520_000,
                "protected_revenue_per_day": 2_400_000,
                "agent_source": agent_source,
            }
        ),
        trigger_event_id=risk_event_id,
    )
    db.add(decision)
    await db.flush()
    await db.commit()
    created["decision_ids"].append(decision.id)

    await publish_event(
        "agent_action",
        {
            "action": "Mitigation plan proposed — awaiting approval",
            "agent_type": "strategy",
            "decision_type": "mitigation_plan",
            "decision_id": decision.id,
            "status": "proposed",
            "source": agent_source,
        },
    )


# ---------------------------------------------------------------------------
# Main demo sequence
# ---------------------------------------------------------------------------


async def run_demo(db: AsyncSession) -> dict:
    """Execute the full demo sequence using real service calls.

    Returns a summary of created entity IDs for cleanup.
    """
    demo_id = str(uuid.uuid4())
    cancel_event = asyncio.Event()

    async with _demo_lock:
        # Cancel any previously running demo
        for old_id, old_ev in _active_demo.items():
            old_ev.set()
        _active_demo.clear()
        _active_demo[demo_id] = cancel_event

    created: dict[str, list[str]] = {
        "risk_event_ids": [],
        "simulation_ids": [],
        "decision_ids": [],
        "handoff_ids": [],
    }

    try:
        # ── Step 0: Start ──────────────────────────────────────────────
        await _publish_step("start", demo_id=demo_id)
        await asyncio.sleep(1.5)

        if await _is_cancelled(demo_id):
            return {"demo_id": demo_id, "status": "cancelled", "created": created}

        # ── Step 1: Inject a critical risk event ───────────────────────
        risk_event = await risk_service.create_risk_event(
            db,
            RiskEventCreate(
                event_type="geopolitical",
                title="Suez Canal Emergency Closure",
                description=(
                    "Vessel collision has blocked both channels of the Suez Canal. "
                    "Egyptian authorities estimate 7-14 day clearance. "
                    "40% of Asia-Europe container traffic is affected."
                ),
                severity="critical",
                severity_score=0.95,
                affected_region="Middle East",
                expected_end=datetime.now(timezone.utc) + timedelta(days=10),
            ),
        )
        await db.commit()
        created["risk_event_ids"].append(risk_event.id)

        await _publish_step(
            "risk_created",
            panel="section-risk",
            risk_event_id=risk_event.id,
        )
        await asyncio.sleep(3.0)

        if await _is_cancelled(demo_id):
            return {"demo_id": demo_id, "status": "cancelled", "created": created}

        # ── Step 2: Automated risk triage ──────────────────────────────
        triage_summary = await run_triage(db, new_event_count=1)
        await db.commit()

        await _publish_step(
            "triage_complete",
            panel="section-suppliers",
            triage=triage_summary,
        )
        await asyncio.sleep(3.0)

        if await _is_cancelled(demo_id):
            return {"demo_id": demo_id, "status": "cancelled", "created": created}

        # ── Step 3: Monte Carlo simulation ─────────────────────────────
        await _publish_step("simulation_running", panel="section-sim")

        sim = await simulation_service.create_simulation(
            db,
            SimulationCreate(
                name="Suez Canal Closure Impact Analysis",
                description="Monte Carlo simulation of 90-day impact from Suez Canal closure",
                scenario_params={"preset": "suez_closure"},
                iterations=10_000,
            ),
        )
        sim = await simulation_service.run_simulation(db, sim.id)
        await db.commit()
        created["simulation_ids"].append(sim.id)

        await _publish_step(
            "simulation_complete",
            panel="section-sim",
            simulation_id=sim.id,
        )
        await asyncio.sleep(3.0)

        if await _is_cancelled(demo_id):
            return {"demo_id": demo_id, "status": "cancelled", "created": created}

        # ── Step 4: Agent deliberation ─────────────────────────────────
        #
        # Three-tier fallback:
        #   1. Claude API  → full orchestrator with specialist handoffs
        #   2. Gemma 4 2B  → local Ollama model generates reasoning
        #   3. Mock data   → hardcoded realistic responses
        #
        agent_tier = await _resolve_agent_tier()
        await _publish_step(
            "agents_deliberating",
            panel="section-agents",
            agent_tier=agent_tier,
        )
        logger.info("Demo agent tier: %s", agent_tier)

        if agent_tier == "claude":
            from app.agents.orchestrator import handle_chat

            try:
                await handle_chat(
                    "A critical Suez Canal closure has been detected. "
                    "Analyze the risk exposure, review the simulation results, "
                    "and propose a mitigation strategy with cost estimates.",
                    db,
                )
                await db.commit()
            except Exception:
                logger.exception("Claude agent failed — falling back")
                agent_tier = "gemma" if await ollama_available() else "mock"

        if agent_tier in ("gemma", "mock"):
            await _run_local_agent_pipeline(
                db,
                risk_event.id,
                created,
                use_gemma=(agent_tier == "gemma"),
            )

        await asyncio.sleep(2.0)

        if await _is_cancelled(demo_id):
            return {"demo_id": demo_id, "status": "cancelled", "created": created}

        # ── Step 5: Mitigation proposed ────────────────────────────────
        await _publish_step("mitigation_proposed", panel="section-agents")
        await asyncio.sleep(2.5)

        # ── Step 6: Approval gate ──────────────────────────────────────
        await _publish_step(
            "approval_gate",
            panel="section-agents",
            message="Human-in-the-loop approval required",
        )
        await asyncio.sleep(3.0)

        # ── Step 7: Complete ───────────────────────────────────────────
        await _publish_step(
            "complete",
            demo_id=demo_id,
            simulation_id=created["simulation_ids"][0] if created["simulation_ids"] else None,
        )

        return {"demo_id": demo_id, "status": "completed", "created": created}

    except Exception:
        logger.exception("Demo sequence failed")
        await _publish_step("complete", demo_id=demo_id, error=True)
        return {"demo_id": demo_id, "status": "error", "created": created}

    finally:
        _active_demo.pop(demo_id, None)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


async def cancel_demo() -> dict:
    """Cancel the currently running demo, if any."""
    for demo_id, ev in _active_demo.items():
        ev.set()
        await _publish_step("complete", demo_id=demo_id, cancelled=True)
        return {"demo_id": demo_id, "status": "cancelled"}
    return {"status": "no_active_demo"}
