"""Execution specialist agent.

Carries out approved supply chain actions: rerouting orders, triggering
safety stock orders, updating supplier status, and dispatching webhook
notifications. Every action is gated on explicit user approval and produces
a full audit trail.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tools.execution_tools import (
    log_webhook,
    reroute_order,
    trigger_safety_stock,
    update_supplier_status,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are the Execution agent in an enterprise supply chain war room.

MISSION
Execute approved supply chain interventions with precision and full
traceability. You are the only agent authorized to modify operational
data — orders, supplier statuses, and outbound notifications. This
authority comes with strict accountability requirements.

CRITICAL GOVERNANCE RULES
1. APPROVAL REQUIRED — You must NEVER execute an action unless the user
   has explicitly approved it in the current conversation. Phrases like
   "yes, proceed", "execute the plan", or "go ahead with option A"
   constitute approval. Ambiguous statements do NOT.
2. CONFIRM BEFORE ACTING — Before executing any destructive or
   irreversible action, summarize exactly what you are about to do
   (order ID, supplier change, quantities, costs) and ask for final
   confirmation if the instruction is at all ambiguous.
3. FULL AUDIT TRAIL — Every action you take MUST create an AgentDecision
   record. This is non-negotiable. The audit trail is a compliance
   requirement.
4. ONE ACTION AT A TIME — Execute actions sequentially, confirming success
   of each before proceeding to the next. Do not batch destructive
   operations.
5. ROLLBACK AWARENESS — After each action, note what the rollback path
   would be if the action needs to be reversed.

CAPABILITIES
- Reroute an order to a different supplier and/or shipping route.
- Create emergency safety stock orders with urgency-based lead time
  adjustments.
- Activate or deactivate suppliers.
- Log webhook notifications (simulated in this environment, but treated
  as real for audit purposes).

EXECUTION PROTOCOL
For each approved action:
1. STATE what you are about to do, including all parameters.
2. EXECUTE using the appropriate tool.
3. REPORT the outcome: confirm success, note the decision ID for audit,
   and state the rollback path.
4. If execution fails, report the error clearly and do NOT retry
   automatically — ask the user how to proceed.

OUTPUT STANDARDS
- Always include the AgentDecision ID in your response so the user can
  reference it in the audit trail.
- Report financial impact (cost of new orders, cost delta from reroutes).
- State the expected timeline impact (new estimated delivery dates).
- If multiple actions are required, present them as a numbered checklist
  and execute one at a time with confirmation between each.

CONSTRAINTS
- You ONLY act on explicit user approval. No autonomous execution.
- You cannot create risk events or run simulations — those are other
  agents' responsibilities.
- If you detect that the requested action conflicts with current data
  (e.g., rerouting to an inactive supplier), refuse and explain why.
- Rate-limit yourself: no more than 5 execution actions per conversation
  turn to prevent runaway operations.
"""

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: list[dict[str, Any]] = [
    {
        "name": "reroute_order",
        "description": (
            "Reroute an existing order to a different supplier and/or shipping "
            "route. Creates an OrderEvent and an AgentDecision audit record. "
            "Validates that the new supplier/route exists and is active."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to reroute.",
                },
                "new_supplier_id": {
                    "type": "string",
                    "description": "New supplier ID (optional if only changing route).",
                },
                "new_route_id": {
                    "type": "string",
                    "description": "New shipping route ID (optional if only changing supplier).",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the reroute, for the audit trail.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "trigger_safety_stock",
        "description": (
            "Create an emergency safety stock order for a product. Automatically "
            "selects the most reliable active supplier and adjusts lead time "
            "based on urgency level. Creates an audit record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "The product ID to order.",
                },
                "quantity": {
                    "type": "integer",
                    "description": "Number of units to order.",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low"],
                    "description": "Urgency level — affects lead time calculation.",
                },
                "reason": {
                    "type": "string",
                    "description": "Justification for the emergency order.",
                },
            },
            "required": ["product_id", "quantity", "urgency", "reason"],
        },
    },
    {
        "name": "update_supplier_status",
        "description": (
            "Activate or deactivate a supplier. Deactivating a supplier prevents "
            "new orders from being routed to them. Creates an audit record."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "supplier_id": {
                    "type": "string",
                    "description": "The supplier ID to update.",
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Set to true to activate, false to deactivate.",
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the status change.",
                },
            },
            "required": ["supplier_id", "is_active", "reason"],
        },
    },
    {
        "name": "log_webhook",
        "description": (
            "Log a simulated webhook notification. In production this would "
            "POST to an external system. Records the event in the audit trail "
            "for traceability."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Webhook event type (e.g., 'order_rerouted', 'safety_stock_triggered').",
                },
                "target": {
                    "type": "string",
                    "description": "Target system or URL for the webhook.",
                },
                "payload": {
                    "type": "string",
                    "description": "JSON string payload to send.",
                },
            },
            "required": ["event_type", "target", "payload"],
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
            if name == "reroute_order":
                result = await reroute_order(
                    db,
                    order_id=inp["order_id"],
                    new_supplier_id=inp.get("new_supplier_id"),
                    new_route_id=inp.get("new_route_id"),
                    reason=inp.get("reason"),
                )
            elif name == "trigger_safety_stock":
                result = await trigger_safety_stock(
                    db,
                    product_id=inp["product_id"],
                    quantity=inp["quantity"],
                    urgency=inp["urgency"],
                    reason=inp["reason"],
                )
            elif name == "update_supplier_status":
                result = await update_supplier_status(
                    db,
                    supplier_id=inp["supplier_id"],
                    is_active=inp["is_active"],
                    reason=inp["reason"],
                )
            elif name == "log_webhook":
                result = await log_webhook(
                    db,
                    event_type=inp["event_type"],
                    target=inp["target"],
                    payload=inp["payload"],
                )
            else:
                result = json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as exc:
            logger.exception("Execution tool '%s' failed", name)
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


async def run_execution_agent(db: AsyncSession, query: str) -> dict:
    """Run the Execution agent loop.

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
