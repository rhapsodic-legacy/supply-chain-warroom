"""Orchestrator — the hub agent for the Supply Chain War Room.

Receives user messages, determines which specialist agent(s) to invoke,
synthesizes their outputs, and maintains conversational context. Also
provides direct database queries for decision logs and war room status.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any

import anthropic
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.execution_agent import run_execution_agent
from app.agents.risk_monitor import run_risk_monitor
from app.agents.simulation_agent import run_simulation_agent
from app.agents.strategy_agent import run_strategy_agent
from app.models import AgentDecision, AgentHandoff, Order, RiskEvent, Simulation
from app.routers.stream import publish_event
from app.schemas import ChatResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Orchestrator of an enterprise supply chain war room powered by AI.

ROLE
You are the command center. Users interact with you, and you coordinate a
team of four specialist agents to deliver comprehensive supply chain
intelligence and execute approved interventions.

YOUR SPECIALIST TEAM
1. RISK MONITOR — Assesses current risks, scores supplier reliability,
   detects emerging threats. Invoke for questions about risk exposure,
   supplier health, regional threats, or when the user needs a risk
   assessment before making decisions.

2. SIMULATION — Runs Monte Carlo what-if analyses. Invoke when the user
   asks "what if", wants to model a disruption scenario, or needs
   probabilistic impact analysis to support a decision.

3. STRATEGY — Generates costed mitigation plans and evaluates alternatives.
   Invoke when the user needs recommendations, contingency plans,
   supplier alternatives, or cost-benefit comparisons.

4. EXECUTION — Carries out approved actions (reroute orders, trigger safety
   stock, update suppliers, send notifications). ONLY invoke after the
   user has explicitly approved a specific plan. Never route to Execution
   speculatively.

ROUTING RULES
- Risk questions -> risk_monitor
- "What if" / scenario questions -> simulation
- "What should we do?" / recommendation requests -> strategy
- "Do it" / "Execute" / explicit approval -> execution
- Audit trail / decision history -> query_decision_log
- General status / overview -> get_war_room_context

MULTI-AGENT WORKFLOWS
Some queries require multiple agents in sequence:
- "Assess the risk and recommend a plan" -> risk_monitor first, then
  strategy with the risk context.
- "Simulate a Suez closure and tell me what to do" -> simulation first,
  then strategy with the simulation results.
- Present the combined output as a coherent narrative, not disjointed
  agent dumps.

COMMUNICATION STYLE
- Professional but accessible. Avoid jargon unless the user uses it first.
- Lead with the answer, then provide supporting detail.
- When presenting specialist agent output, add your own synthesis and
  highlight the key takeaways.
- If a question is ambiguous, ask a clarifying question rather than
  guessing — but offer your best interpretation as a default.
- When actions are available, present them clearly with a call-to-action
  (e.g., "Would you like me to execute this plan?").

SAFETY AND GOVERNANCE
- Never execute supply chain actions without explicit user approval.
- Always surface costs, risks, and trade-offs before recommending action.
- If a specialist agent returns an error, explain the issue clearly and
  suggest alternatives rather than silently failing.
- Maintain context across the conversation — reference earlier findings
  when they are relevant to the current question.
"""

# ---------------------------------------------------------------------------
# Orchestrator tool definitions
# ---------------------------------------------------------------------------

ORCHESTRATOR_TOOLS: list[dict[str, Any]] = [
    {
        "name": "risk_monitor",
        "description": (
            "Analyze current supply chain risks, score suppliers, detect threats. "
            "Use for: 'What risks do we face?', 'How reliable is supplier X?', "
            "'What's happening in region Y?', 'Are there any active alerts?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The risk-related question or analysis request to send to the Risk Monitor agent.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "simulation",
        "description": (
            "Run what-if scenario simulations using Monte Carlo analysis. "
            "Use for: 'What if the Suez Canal closes?', 'Simulate a demand spike', "
            "'Model a supplier failure', 'What are the worst-case outcomes?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The simulation question or scenario to model.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "strategy",
        "description": (
            "Generate mitigation strategies, find alternative suppliers, and run "
            "cost-benefit analyses. Use for: 'What should we do about X?', "
            "'Recommend alternatives', 'Create a contingency plan', 'Compare options'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The strategy question or recommendation request.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "execution",
        "description": (
            "Execute approved supply chain actions. ONLY use after the user has "
            "explicitly approved a strategy. Use for: 'Execute the plan', "
            "'Reroute order X', 'Yes, proceed', 'Go ahead with option A'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The execution instruction including specific parameters.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_decision_log",
        "description": (
            "Look up past agent decisions, reasoning, and audit trails. "
            "Use for: 'Why did you reroute order X?', 'What decisions were made?', "
            "'Show me the audit trail', 'What has the execution agent done?'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What kind of decisions to look up.",
                },
                "agent_type": {
                    "type": "string",
                    "enum": ["risk_monitor", "simulation", "strategy", "execution"],
                    "description": "Filter by agent type.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of decisions to return. Default 10.",
                },
            },
        },
    },
    {
        "name": "get_war_room_context",
        "description": (
            "Get current war room status: active alerts, recent simulations, "
            "pending strategies, recent execution decisions, and order pipeline "
            "summary. Use as a starting point for broad status questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# Direct database tools (no specialist agent needed)
# ---------------------------------------------------------------------------


async def _query_decision_log(
    db: AsyncSession,
    agent_type: str | None = None,
    limit: int = 10,
) -> str:
    """Query the agent decision log from the database."""
    stmt = select(AgentDecision).order_by(AgentDecision.decided_at.desc()).limit(limit)
    if agent_type:
        stmt = stmt.where(AgentDecision.agent_type == agent_type)

    result = await db.execute(stmt)
    decisions = result.scalars().all()

    return json.dumps(
        [
            {
                "id": d.id,
                "agent_type": d.agent_type,
                "decision_type": d.decision_type,
                "summary": d.decision_summary,
                "reasoning": d.reasoning[:200] + "..." if len(d.reasoning) > 200 else d.reasoning,
                "confidence": float(d.confidence_score),
                "status": d.status,
                "cost_impact": float(d.cost_impact) if d.cost_impact else None,
                "decided_at": d.decided_at.isoformat() if d.decided_at else None,
                "executed_at": d.executed_at.isoformat() if d.executed_at else None,
            }
            for d in decisions
        ],
        default=str,
    )


async def _get_war_room_context(db: AsyncSession) -> str:
    """Assemble a snapshot of the current war room state."""
    # Active risk events
    risk_result = await db.execute(
        select(func.count(RiskEvent.id)).where(RiskEvent.is_active.is_(True))
    )
    active_risks = risk_result.scalar() or 0

    critical_result = await db.execute(
        select(func.count(RiskEvent.id)).where(
            RiskEvent.is_active.is_(True), RiskEvent.severity == "critical"
        )
    )
    critical_risks = critical_result.scalar() or 0

    # Recent simulations
    sim_result = await db.execute(
        select(Simulation).order_by(Simulation.created_at.desc()).limit(5)
    )
    recent_sims = sim_result.scalars().all()

    # Pending strategy decisions
    pending_result = await db.execute(
        select(AgentDecision)
        .where(AgentDecision.status == "proposed")
        .order_by(AgentDecision.decided_at.desc())
        .limit(5)
    )
    pending_strategies = pending_result.scalars().all()

    # Recent executed decisions
    executed_result = await db.execute(
        select(AgentDecision)
        .where(AgentDecision.status == "executed")
        .order_by(AgentDecision.executed_at.desc())
        .limit(5)
    )
    recent_executions = executed_result.scalars().all()

    # Order pipeline summary
    pipeline_result = await db.execute(
        select(Order.status, func.count(Order.id), func.sum(Order.total_cost)).group_by(
            Order.status
        )
    )
    pipeline = [
        {"status": row[0], "count": row[1], "total_cost": float(row[2] or 0)}
        for row in pipeline_result.all()
    ]

    context = {
        "active_risk_events": active_risks,
        "critical_risk_events": critical_risks,
        "recent_simulations": [
            {
                "id": s.id,
                "name": s.name,
                "status": s.status,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in recent_sims
        ],
        "pending_strategies": [
            {
                "id": d.id,
                "summary": d.decision_summary,
                "cost_impact": float(d.cost_impact) if d.cost_impact else None,
                "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            }
            for d in pending_strategies
        ],
        "recent_executions": [
            {
                "id": d.id,
                "summary": d.decision_summary,
                "status": d.status,
                "executed_at": d.executed_at.isoformat() if d.executed_at else None,
            }
            for d in recent_executions
        ],
        "order_pipeline": pipeline,
    }
    return json.dumps(context, default=str)


# ---------------------------------------------------------------------------
# Tool execution dispatcher
# ---------------------------------------------------------------------------


# Agent tools that represent actual specialist handoffs (not direct DB queries)
_SPECIALIST_AGENTS = {"risk_monitor", "simulation", "strategy", "execution"}


async def _execute_orchestrator_tool(
    tool_name: str,
    tool_input: dict,
    db: AsyncSession,
    session_id: str | None = None,
    sequence: int = 0,
) -> str:
    """Dispatch an orchestrator tool call to the appropriate handler.

    When the tool is a specialist agent, creates a handoff record and
    broadcasts SSE events for pipeline visibility.
    """
    is_handoff = tool_name in _SPECIALIST_AGENTS and session_id is not None

    handoff: AgentHandoff | None = None
    if is_handoff:
        handoff = AgentHandoff(
            session_id=session_id,
            sequence=sequence,
            from_agent="orchestrator",
            to_agent=tool_name,
            query=tool_input.get("query", ""),
            status="running",
        )
        db.add(handoff)
        await db.flush()

        await publish_event("agent_handoff", {
            "handoff_id": handoff.id,
            "session_id": session_id,
            "sequence": sequence,
            "from_agent": "orchestrator",
            "to_agent": tool_name,
            "query": tool_input.get("query", ""),
            "status": "running",
        })

    start = time.monotonic()

    try:
        if tool_name == "risk_monitor":
            result = await run_risk_monitor(db, tool_input["query"])
            response_text = result["response"]

        elif tool_name == "simulation":
            result = await run_simulation_agent(db, tool_input["query"])
            response_text = result["response"]

        elif tool_name == "strategy":
            result = await run_strategy_agent(db, tool_input["query"])
            response_text = result["response"]

        elif tool_name == "execution":
            result = await run_execution_agent(db, tool_input["query"])
            response_text = result["response"]

        elif tool_name == "query_decision_log":
            return await _query_decision_log(
                db,
                agent_type=tool_input.get("agent_type"),
                limit=tool_input.get("limit", 10),
            )

        elif tool_name == "get_war_room_context":
            return await _get_war_room_context(db)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        # Record successful handoff completion
        if handoff:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            handoff.status = "completed"
            handoff.completed_at = datetime.utcnow()
            handoff.duration_ms = elapsed_ms
            handoff.result_summary = response_text[:300] if response_text else None
            await db.flush()

            await publish_event("agent_handoff", {
                "handoff_id": handoff.id,
                "session_id": session_id,
                "sequence": sequence,
                "from_agent": "orchestrator",
                "to_agent": tool_name,
                "status": "completed",
                "duration_ms": elapsed_ms,
            })

        return response_text

    except Exception as exc:
        logger.exception("Orchestrator tool '%s' failed", tool_name)

        if handoff:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            handoff.status = "error"
            handoff.completed_at = datetime.utcnow()
            handoff.duration_ms = elapsed_ms
            handoff.result_summary = str(exc)[:300]
            await db.flush()

            await publish_event("agent_handoff", {
                "handoff_id": handoff.id,
                "session_id": session_id,
                "sequence": sequence,
                "from_agent": "orchestrator",
                "to_agent": tool_name,
                "status": "error",
                "duration_ms": elapsed_ms,
            })

        return json.dumps({"error": f"Tool '{tool_name}' failed: {str(exc)}"})


# ---------------------------------------------------------------------------
# Orchestrator agent loop
# ---------------------------------------------------------------------------


async def run_orchestrator(db: AsyncSession, message: str) -> dict:
    """Run the orchestrator agent loop.

    Returns ``{"response": str, "actions": list[dict], "session_id": str}``.
    """
    client = anthropic.AsyncAnthropic()
    messages: list[dict[str, Any]] = [{"role": "user", "content": message}]
    all_actions: list[dict] = []
    session_id = str(uuid.uuid4())
    sequence_counter = 0

    while True:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=ORCHESTRATOR_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            # Process all tool calls in the response
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue

                tool_result_str = await _execute_orchestrator_tool(
                    block.name,
                    block.input,
                    db,
                    session_id=session_id,
                    sequence=sequence_counter,
                )
                sequence_counter += 1

                all_actions.append(
                    {
                        "agent": block.name,
                        "input": block.input,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result_str,
                    }
                )

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            # Extract final text response
            text_parts = []
            for block in response.content:
                if hasattr(block, "text"):
                    text_parts.append(block.text)

            return {
                "response": "\n".join(text_parts),
                "actions": all_actions,
                "session_id": session_id,
            }


# ---------------------------------------------------------------------------
# FastAPI entry point (called by routers/agents.py)
# ---------------------------------------------------------------------------


async def handle_chat(message: str, db: AsyncSession) -> ChatResponse:
    """Entry point called by the /api/v1/agents/chat endpoint."""
    result = await run_orchestrator(db, message)
    return ChatResponse(
        response=result["response"],
        agent_actions=result.get("actions", []),
        timestamp=datetime.utcnow(),
    )
