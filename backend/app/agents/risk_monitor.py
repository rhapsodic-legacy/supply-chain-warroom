"""Risk Monitor specialist agent.

Assesses supply chain risks, scores supplier reliability, detects emerging
threats, and raises alerts when intervention thresholds are crossed.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.risk_tools import (
    create_alert,
    fetch_risk_signals,
    query_risk_events,
    score_suppliers,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Risk Monitor agent embedded in an enterprise supply chain war room.

MISSION
Continuously assess supply chain risk exposure and provide decision-ready
intelligence to the Orchestrator. Your analysis directly informs whether
the organization activates contingency plans, so precision and clarity matter.

CAPABILITIES
- Query active and historical risk events (geopolitical, weather, logistics,
  compliance, supplier-specific).
- Compute composite supplier risk scores that blend reliability history,
  regional threat density, and financial exposure from open purchase orders.
- Ingest demand anomaly signals that may indicate forecasting failures or
  market shifts.
- Create new risk alerts when you identify emerging threats that are not
  yet in the database.

ANALYSIS FRAMEWORK
When assessing risk, apply this structured approach:
1. IDENTIFICATION — What is the threat? Classify by type (geopolitical,
   natural disaster, supplier failure, logistics bottleneck, demand shock).
2. PROBABILITY — How likely is impact? Use severity scores and historical
   patterns.
3. IMPACT — What is the blast radius? Which suppliers, routes, products,
   and orders are exposed?
4. VELOCITY — How fast is the threat developing? Is there lead time to
   respond?
5. INTERCONNECTION — Could this trigger cascading failures elsewhere in
   the network?

OUTPUT STANDARDS
- Lead with the bottom line: state the risk level and recommended urgency
  before diving into detail.
- Quantify wherever possible (dollar exposure, days of delay, percentage
  of capacity affected).
- When scoring suppliers, explain the drivers behind the score so the user
  can act on it.
- If the data is insufficient for a confident assessment, say so explicitly
  and recommend what additional information would resolve the ambiguity.

CONSTRAINTS
- You are read-only with respect to orders and suppliers — you observe but
  do not modify operational data.
- The only write action you may take is creating risk alerts via
  create_alert when you identify a credible emerging threat.
- Always cite specific risk event IDs or supplier IDs when referencing data.
"""

# ---------------------------------------------------------------------------
# Tool definitions (Anthropic tool-use schema)
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "query_risk_events",
        "description": (
            "Retrieve risk events from the database. Supports filtering by "
            "active status, severity level (low/medium/high/critical), and "
            "affected geographic region."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "active_only": {
                    "type": "boolean",
                    "description": "If true, return only currently active risk events. Default true.",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Filter by severity level.",
                },
                "region": {
                    "type": "string",
                    "description": "Filter by affected geographic region (e.g. 'East Asia', 'Europe').",
                },
            },
        },
    },
    {
        "name": "score_suppliers",
        "description": (
            "Compute composite risk scores for all active suppliers. Scores "
            "combine reliability history, count of active regional risk events, "
            "and financial exposure from in-flight orders. Optionally filter by region."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "description": "Optional region filter (e.g. 'East Asia').",
                },
            },
        },
    },
    {
        "name": "fetch_risk_signals",
        "description": (
            "Aggregate recent risk events and demand anomalies into a unified "
            "signals feed. Use this for broad situational awareness or when "
            "looking for emerging patterns across risk types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "create_alert",
        "description": (
            "Create a new risk alert when you identify an emerging threat not "
            "already tracked in the system. Provide a clear title, description, "
            "and severity assessment."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Concise alert title.",
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the identified threat.",
                },
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "critical"],
                    "description": "Assessed severity level.",
                },
                "severity_score": {
                    "type": "number",
                    "description": "Numeric severity score from 0.0 to 1.0.",
                },
                "affected_region": {
                    "type": "string",
                    "description": "Geographic region affected by the threat.",
                },
                "event_type": {
                    "type": "string",
                    "description": "Type of risk event (e.g. 'geopolitical', 'weather', 'logistics', 'agent_alert').",
                },
            },
            "required": ["title", "description", "severity", "severity_score"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution dispatcher
# ---------------------------------------------------------------------------


async def _execute_tools(response: anthropic.types.Message, db: AsyncSession) -> list[dict]:
    """Execute tool calls from a model response, return tool_result blocks."""
    tool_results = []
    for block in response.content:
        if block.type != "tool_use":
            continue

        name = block.name
        inp = block.input
        tool_id = block.id

        try:
            if name == "query_risk_events":
                result = await query_risk_events(
                    db,
                    active_only=inp.get("active_only", True),
                    severity=inp.get("severity"),
                    region=inp.get("region"),
                )
            elif name == "score_suppliers":
                result = await score_suppliers(db, region=inp.get("region"))
            elif name == "fetch_risk_signals":
                result = await fetch_risk_signals(db)
            elif name == "create_alert":
                result = await create_alert(
                    db,
                    title=inp["title"],
                    description=inp["description"],
                    severity=inp["severity"],
                    severity_score=inp["severity_score"],
                    affected_region=inp.get("affected_region"),
                    event_type=inp.get("event_type", "agent_alert"),
                )
            else:
                result = json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as exc:
            logger.exception("Risk Monitor tool '%s' failed", name)
            result = json.dumps({"error": str(exc)})

        tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})
    return tool_results


# ---------------------------------------------------------------------------
# Agent entry point
# ---------------------------------------------------------------------------


def _extract_response(response: anthropic.types.Message) -> dict:
    """Pull text and action metadata from a final model response."""
    text_parts = []
    actions = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    return {"response": "\n".join(text_parts), "actions": actions}


async def run_risk_monitor(db: AsyncSession, query: str) -> dict:
    """Run the Risk Monitor agent loop.

    Returns ``{"response": str, "actions": list[dict]}``.
    """
    client = anthropic.AsyncAnthropic()
    messages: list[dict[str, Any]] = [{"role": "user", "content": query}]

    while True:
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            tool_results = await _execute_tools(response, db)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            return _extract_response(response)
