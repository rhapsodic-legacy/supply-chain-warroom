"""Simulation specialist agent.

Runs Monte Carlo disruption simulations, interprets statistical outputs,
and translates probability distributions into business-relevant language.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.simulation_tools import (
    list_preset_scenarios,
    query_network_stats,
    run_monte_carlo,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Simulation agent in an enterprise supply chain war room.

MISSION
Run quantitative what-if analyses using Monte Carlo simulation to help
leadership understand the probabilistic impact of supply chain disruptions
before they commit resources. Your outputs must bridge the gap between raw
statistics and executive decision-making.

CAPABILITIES
- List available preset disruption scenarios (Suez Canal closure, Shanghai
  port congestion, single-source supplier failure, demand shock).
- Execute Monte Carlo simulations with configurable iteration counts and
  custom or preset scenarios.
- Query the current supply chain network topology (nodes, edges, routes,
  transport modes, reliability metrics).

HOW TO INTERPRET RESULTS
After running a simulation, always explain:
1. BASELINE vs. DISRUPTED — How does the disrupted scenario compare to
   normal operations across cost, delay, and fill rate?
2. TAIL RISK — What do the P90, P95, and P99 values tell us about
   worst-case outcomes? These matter more than means for risk management.
3. COST AT RISK — Translate cost distribution into dollar terms. Frame
   P95 cost as "there is a 5% chance costs will exceed $X."
4. SERVICE LEVEL IMPACT — What happens to fill rate? A drop below 0.90
   is operationally significant; below 0.80 is a crisis.
5. STOCKOUT PROBABILITY — How many days of complete supply interruption
   should we plan for?

OUTPUT STANDARDS
- Always state iteration count and scenario name at the top of your analysis.
- Use tables or structured formatting for distribution statistics.
- Compare to baseline with both absolute and percentage differences.
- Provide a plain-language "so what" — what should the war room do with
  this information?
- If the simulation reveals severe tail risk (P95 cost >2x baseline or
  fill rate P5 <0.80), flag it prominently.

CONSTRAINTS
- You do not modify orders, suppliers, or routes. You only simulate.
- For custom scenarios, validate that disruption parameters are physically
  plausible before running (e.g., severity between 0 and 1).
- If asked about a scenario that does not match a preset, construct custom
  scenario_params and explain your modeling assumptions.
"""

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "list_preset_scenarios",
        "description": (
            "Return the catalogue of available preset disruption scenarios "
            "with their names, descriptions, and disruption types."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "run_monte_carlo",
        "description": (
            "Execute a Monte Carlo simulation on the current supply chain "
            "network. Provide either a preset scenario name or custom "
            "scenario parameters. Returns distribution statistics for cost, "
            "delay, fill rate, and stockouts, compared against baseline."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scenario_name": {
                    "type": "string",
                    "description": (
                        "Key of a preset scenario (e.g. 'suez_canal_closure', "
                        "'shanghai_port_congestion', 'single_source_supplier_failure', "
                        "'demand_shock'). Mutually exclusive with scenario_params."
                    ),
                },
                "scenario_params": {
                    "type": "object",
                    "description": (
                        "Custom scenario definition. Shape: "
                        '{"name": "...", "description": "...", "time_horizon_days": 90, '
                        '"disruptions": [{"type": "...", "severity": 0.8, "duration_days": 14, ...}]}'
                    ),
                },
                "iterations": {
                    "type": "integer",
                    "description": "Number of Monte Carlo iterations. Default 10000. Use 1000 for quick estimates.",
                },
            },
        },
    },
    {
        "name": "query_network_stats",
        "description": (
            "Get a summary of the current supply chain network graph: node "
            "counts by type, edge counts, average reliability, transport "
            "modes, and covered regions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution dispatcher
# ---------------------------------------------------------------------------


async def _execute_tools(response: anthropic.types.Message, db: AsyncSession) -> list[dict]:
    """Execute tool calls and return tool_result content blocks."""
    tool_results = []
    for block in response.content:
        if block.type != "tool_use":
            continue

        name = block.name
        inp = block.input
        tool_id = block.id

        try:
            if name == "list_preset_scenarios":
                result = await list_preset_scenarios()
            elif name == "run_monte_carlo":
                result = await run_monte_carlo(
                    db,
                    scenario_name=inp.get("scenario_name"),
                    scenario_params=inp.get("scenario_params"),
                    iterations=inp.get("iterations", 10_000),
                )
            elif name == "query_network_stats":
                result = await query_network_stats(db)
            else:
                result = json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as exc:
            logger.exception("Simulation tool '%s' failed", name)
            result = json.dumps({"error": str(exc)})

        tool_results.append({"type": "tool_result", "tool_use_id": tool_id, "content": result})
    return tool_results


# ---------------------------------------------------------------------------
# Agent entry point
# ---------------------------------------------------------------------------


def _extract_response(response: anthropic.types.Message) -> dict:
    """Pull text from a final model response."""
    text_parts = []
    actions = []
    for block in response.content:
        if hasattr(block, "text"):
            text_parts.append(block.text)
    return {"response": "\n".join(text_parts), "actions": actions}


async def run_simulation_agent(db: AsyncSession, query: str) -> dict:
    """Run the Simulation agent loop.

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
