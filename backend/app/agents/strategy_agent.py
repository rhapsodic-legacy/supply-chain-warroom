"""Strategy specialist agent.

Generates mitigation strategies, evaluates alternatives, runs cost-benefit
analyses, and produces actionable contingency plans for user approval.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.strategy_tools import (
    cost_benefit_analysis,
    generate_mitigation_plan,
    query_alternative_suppliers,
    query_inventory_status,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Strategy agent in an enterprise supply chain war room.

MISSION
Translate risk intelligence and simulation results into concrete, costed
mitigation strategies that leadership can approve or reject. You are the
bridge between "we have a problem" and "here is what we should do about it."

CAPABILITIES
- Query current inventory and order pipeline status across all products and
  statuses to understand the starting position.
- Search for alternative suppliers when a primary source is compromised,
  ranked by reliability, cost, and lead time.
- Author formal mitigation plans that are persisted for audit and later
  execution. Plans are saved with status "proposed" until the user approves.
- Run structured cost-benefit analyses comparing current-state costs against
  proposed changes, accounting for delay reduction and risk reduction value.

STRATEGY DEVELOPMENT PROCESS
1. ASSESS CURRENT STATE — Use query_inventory_status to understand what is
   in the pipeline and what is at risk.
2. IDENTIFY OPTIONS — Use query_alternative_suppliers to find backup sources.
   Consider geographic diversification, lead time trade-offs, and capacity.
3. MODEL TRADE-OFFS — Use cost_benefit_analysis to quantify the financial
   case for each option. Always compare at least two alternatives.
4. FORMULATE PLAN — Use generate_mitigation_plan to persist a structured
   recommendation with specific actions, estimated cost, and expected risk
   reduction.
5. PRESENT FOR APPROVAL — Clearly state what you recommend, what it costs,
   and what risk it mitigates. The user must explicitly approve before any
   execution occurs.

OUTPUT STANDARDS
- Structure recommendations with clear headings: Situation, Options,
  Recommended Action, Cost Impact, Risk Reduction, and Next Steps.
- Always provide at least two options (including "do nothing" as a baseline)
  so the user can make an informed choice.
- Quantify cost impacts in dollars and percentages.
- Express risk reduction as a percentage and explain what it means
  operationally (e.g., "reduces probability of stockout from 35% to 12%").
- If you lack data to produce a confident recommendation, state what
  additional information you need and from which agent (Risk Monitor or
  Simulation).

CONSTRAINTS
- You PROPOSE strategies but never execute them. Execution is the
  responsibility of the Execution agent, triggered only after explicit
  user approval.
- Every mitigation plan must be saved via generate_mitigation_plan so there
  is an auditable record.
- Never recommend single-sourcing as a mitigation strategy — diversification
  is a core principle.
- Consider total cost of ownership, not just unit price, when comparing
  suppliers (include lead time costs, risk premiums, and switching costs).
"""

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "query_inventory_status",
        "description": (
            "Get current order quantities grouped by product and order status. "
            "Shows pending, in-transit, processing, and delivered volumes with "
            "total cost for each product."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "query_alternative_suppliers",
        "description": (
            "Find alternative suppliers that can provide a specific product, "
            "ranked by reliability score. Optionally exclude a specific supplier "
            "(e.g., the one currently at risk)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID to find suppliers for.",
                },
                "exclude_supplier_id": {
                    "type": "string",
                    "description": "Optional supplier ID to exclude from results (e.g., a compromised supplier).",
                },
            },
            "required": ["product_id"],
        },
    },
    {
        "name": "generate_mitigation_plan",
        "description": (
            "Persist a formal mitigation plan as a proposed AgentDecision. "
            "The plan will require user approval before the Execution agent "
            "can act on it. Include a clear description, specific action steps, "
            "estimated cost, and expected risk reduction percentage."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "risk_event_id": {
                    "type": "string",
                    "description": "ID of the risk event this plan mitigates (null if proactive).",
                },
                "strategy_description": {
                    "type": "string",
                    "description": "Plain-language summary of the mitigation strategy.",
                },
                "actions_json": {
                    "type": "string",
                    "description": "JSON string listing specific action steps to execute.",
                },
                "estimated_cost": {
                    "type": "number",
                    "description": "Estimated total cost in USD to implement the strategy.",
                },
                "risk_reduction_pct": {
                    "type": "number",
                    "description": "Expected risk reduction as a percentage (0-100).",
                },
            },
            "required": ["strategy_description", "actions_json", "estimated_cost", "risk_reduction_pct"],
        },
    },
    {
        "name": "cost_benefit_analysis",
        "description": (
            "Run a structured cost-benefit analysis comparing current state "
            "against a proposed change. Computes net benefit, ROI, and a "
            "recommendation based on delay reduction value and risk reduction value."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "current_cost": {
                    "type": "number",
                    "description": "Current total cost in USD under the existing arrangement.",
                },
                "proposed_cost": {
                    "type": "number",
                    "description": "Proposed total cost in USD under the new arrangement.",
                },
                "delay_reduction_days": {
                    "type": "number",
                    "description": "Expected reduction in delivery delay (days).",
                },
                "risk_reduction_pct": {
                    "type": "number",
                    "description": "Expected risk reduction as a percentage (0-100).",
                },
            },
            "required": ["current_cost", "proposed_cost", "delay_reduction_days", "risk_reduction_pct"],
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
            if name == "query_inventory_status":
                result = await query_inventory_status(db)
            elif name == "query_alternative_suppliers":
                result = await query_alternative_suppliers(
                    db,
                    product_id=inp["product_id"],
                    exclude_supplier_id=inp.get("exclude_supplier_id"),
                )
            elif name == "generate_mitigation_plan":
                result = await generate_mitigation_plan(
                    db,
                    risk_event_id=inp.get("risk_event_id"),
                    strategy_description=inp["strategy_description"],
                    actions_json=inp["actions_json"],
                    estimated_cost=inp["estimated_cost"],
                    risk_reduction_pct=inp["risk_reduction_pct"],
                )
            elif name == "cost_benefit_analysis":
                result = await cost_benefit_analysis(
                    db,
                    current_cost=inp["current_cost"],
                    proposed_cost=inp["proposed_cost"],
                    delay_reduction_days=inp["delay_reduction_days"],
                    risk_reduction_pct=inp["risk_reduction_pct"],
                )
            else:
                result = json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as exc:
            logger.exception("Strategy tool '%s' failed", name)
            result = json.dumps({"error": str(exc)})

        tool_results.append(
            {"type": "tool_result", "tool_use_id": tool_id, "content": result}
        )
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


async def run_strategy_agent(db: AsyncSession, query: str) -> dict:
    """Run the Strategy agent loop.

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
