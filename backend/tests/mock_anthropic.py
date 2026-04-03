"""Mock Anthropic client for testing agent workflows without real API calls.

Provides deterministic, scenario-based responses that exercise the full
tool-use loop: the mock returns tool_use blocks that trigger real tool
execution against the test database, then returns a final text response.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Mock data classes that mirror anthropic.types
# ---------------------------------------------------------------------------


@dataclass
class MockContentBlock:
    """Mirrors anthropic.types.ContentBlock (TextBlock or ToolUseBlock)."""

    type: str
    text: str | None = None
    id: str | None = None
    name: str | None = None
    input: dict | None = None


@dataclass
class MockUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class MockResponse:
    """Mirrors anthropic.types.Message."""

    content: list[MockContentBlock]
    stop_reason: str  # "end_turn" or "tool_use"
    model: str = "mock-model"
    usage: dict = field(default_factory=lambda: {"input_tokens": 100, "output_tokens": 50})
    id: str = "msg_mock_001"
    type: str = "message"
    role: str = "assistant"


# ---------------------------------------------------------------------------
# Mock messages API
# ---------------------------------------------------------------------------


class MockAnthropicMessages:
    """Configurable mock that returns scripted responses based on message content.

    Scenarios are matched in order.  Each scenario has a *matcher* callable
    and a list of ``MockResponse`` objects consumed in FIFO order.  When the
    list is exhausted the scenario is skipped on subsequent calls so the
    next matching scenario (or the default) takes over.
    """

    def __init__(self) -> None:
        self._scenarios: list[tuple[Callable, list[MockResponse]]] = []
        self._call_count: int = 0
        self._call_log: list[dict[str, Any]] = []

    # -- configuration helpers ------------------------------------------------

    def add_scenario(
        self,
        matcher: Callable[[list[dict]], bool],
        responses: list[MockResponse],
    ) -> None:
        """Register a scenario.

        *matcher* receives the ``messages`` kwarg from ``create()`` and
        returns ``True`` if this scenario should handle the call.
        *responses* are returned one-at-a-time in order.
        """
        self._scenarios.append((matcher, list(responses)))

    def add_simple_response(self, text: str) -> None:
        """Convenience: always-match scenario with a single text reply."""
        self.add_scenario(
            lambda _msgs: True,
            [
                MockResponse(
                    content=[MockContentBlock(type="text", text=text)],
                    stop_reason="end_turn",
                )
            ],
        )

    # -- core mock ------------------------------------------------------------

    async def create(self, **kwargs: Any) -> MockResponse:
        """Mock ``messages.create()`` — returns the next scripted response."""
        self._call_count += 1
        self._call_log.append(kwargs)
        messages = kwargs.get("messages", [])

        for matcher, responses in self._scenarios:
            try:
                if matcher(messages) and responses:
                    return responses.pop(0)
            except Exception:
                continue

        # Default: simple text response
        return MockResponse(
            content=[
                MockContentBlock(
                    type="text",
                    text="I've analyzed the situation. No immediate concerns detected.",
                )
            ],
            stop_reason="end_turn",
        )


# ---------------------------------------------------------------------------
# Top-level mock client
# ---------------------------------------------------------------------------


class MockAsyncAnthropic:
    """Drop-in replacement for ``anthropic.AsyncAnthropic``."""

    def __init__(self, **_kwargs: Any) -> None:
        self.messages = MockAnthropicMessages()


# =========================================================================
# Pre-built scenario helpers
# =========================================================================


def _tool_use_block(
    tool_name: str,
    tool_input: dict,
    tool_id: str = "toolu_mock_001",
) -> MockContentBlock:
    return MockContentBlock(
        type="tool_use",
        id=tool_id,
        name=tool_name,
        input=tool_input,
    )


def _text_block(text: str) -> MockContentBlock:
    return MockContentBlock(type="text", text=text)


# ---------------------------------------------------------------------------
# Risk assessment scenario
# ---------------------------------------------------------------------------


def risk_assessment_scenario() -> list[MockResponse]:
    """Two-step risk assessment: tool_use for query_risk_events, then text.

    Step 1 (returned on first call): model asks to call ``query_risk_events``.
    Step 2 (returned after tool results are appended): model summarises risks.
    """
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "query_risk_events",
                    {"active_only": True},
                    tool_id="toolu_risk_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    "Based on my analysis of the active risk events, I've identified "
                    "the following key threats:\n\n"
                    "1. **Geopolitical risk** in East Asia — affecting regional suppliers.\n"
                    "2. **Weather disruption** — potential port closures.\n"
                    "3. **Logistics bottleneck** — congestion on key shipping routes.\n\n"
                    "I recommend running a simulation to quantify the financial exposure "
                    "and developing contingency plans for the highest-severity events."
                )
            ],
            stop_reason="end_turn",
        ),
    ]


# ---------------------------------------------------------------------------
# Simulation scenario
# ---------------------------------------------------------------------------


def simulation_scenario(
    scenario_name: str = "suez_canal_closure",
    iterations: int = 1000,
) -> list[MockResponse]:
    """Two-step simulation: tool_use for run_monte_carlo, then analysis text."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "run_monte_carlo",
                    {"scenario_name": scenario_name, "iterations": iterations},
                    tool_id="toolu_sim_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    f"Simulation complete ({iterations} iterations, {scenario_name}).\n\n"
                    "**Key findings:**\n"
                    "- Cost increase: ~15-20% above baseline\n"
                    "- Delay increase: 5-8 days on affected routes\n"
                    "- Fill rate drops from 0.95 to approximately 0.82\n"
                    "- P95 cost-at-risk indicates a 5% chance of costs exceeding 2x baseline\n\n"
                    "This is a significant disruption scenario. I recommend the Strategy agent "
                    "develop contingency plans for affected routes."
                )
            ],
            stop_reason="end_turn",
        ),
    ]


# ---------------------------------------------------------------------------
# Strategy scenario
# ---------------------------------------------------------------------------


def strategy_scenario(
    risk_event_id: str | None = None,
) -> list[MockResponse]:
    """Two-step strategy: tool_use for generate_mitigation_plan, then recommendation."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "generate_mitigation_plan",
                    {
                        "risk_event_id": risk_event_id,
                        "strategy_description": "Diversify supplier base by adding secondary source in Southeast Asia and pre-positioning safety stock for critical components.",
                        "actions_json": '["Onboard backup supplier in Vietnam", "Pre-order 2 weeks safety stock for critical SKUs", "Activate alternate shipping route via Singapore"]',
                        "estimated_cost": 125000.0,
                        "risk_reduction_pct": 45.0,
                    },
                    tool_id="toolu_strat_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    "I've developed a mitigation plan and saved it for your review.\n\n"
                    "**Recommended Strategy:**\n"
                    "1. Onboard backup supplier in Vietnam\n"
                    "2. Pre-order 2 weeks safety stock for critical SKUs\n"
                    "3. Activate alternate shipping route via Singapore\n\n"
                    "**Estimated cost:** $125,000\n"
                    "**Expected risk reduction:** 45%\n\n"
                    "Would you like me to execute this plan?"
                )
            ],
            stop_reason="end_turn",
        ),
    ]


# ---------------------------------------------------------------------------
# Execution scenario
# ---------------------------------------------------------------------------


def execution_scenario(
    order_id: str,
    new_supplier_id: str,
) -> list[MockResponse]:
    """Two-step execution: tool_use for reroute_order, then confirmation."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "reroute_order",
                    {
                        "order_id": order_id,
                        "new_supplier_id": new_supplier_id,
                        "reason": "Rerouting due to supply chain disruption risk mitigation.",
                    },
                    tool_id="toolu_exec_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    f"Order {order_id} has been successfully rerouted to supplier "
                    f"{new_supplier_id}.\n\n"
                    "An audit record has been created. "
                    "The expected delivery timeline may shift by 1-3 days. "
                    "I'll monitor the rerouted order for any further issues."
                )
            ],
            stop_reason="end_turn",
        ),
    ]


# ---------------------------------------------------------------------------
# Orchestrator-level helpers (returns tool_use that calls specialist agents)
# ---------------------------------------------------------------------------


def orchestrator_risk_scenario() -> list[MockResponse]:
    """Orchestrator routes to risk_monitor, then synthesises."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "risk_monitor",
                    {"query": "Assess all active risk events and their severity."},
                    tool_id="toolu_orch_risk_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    "Here is the current risk assessment from our Risk Monitor:\n\n"
                    "We have identified multiple active risk events across our supply chain network. "
                    "The most critical risks involve geopolitical tensions and logistics disruptions "
                    "that could impact delivery timelines and costs.\n\n"
                    "I recommend we run a simulation to quantify the financial exposure."
                )
            ],
            stop_reason="end_turn",
        ),
    ]


def orchestrator_simulation_scenario() -> list[MockResponse]:
    """Orchestrator routes to simulation, then synthesises."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "simulation",
                    {"query": "Simulate a Suez Canal closure for 3 weeks"},
                    tool_id="toolu_orch_sim_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    "The simulation results are in. A 3-week Suez Canal closure would cause "
                    "significant disruption to our supply chain.\n\n"
                    "Key impacts include cost increases and delivery delays on affected routes. "
                    "I recommend the Strategy agent develop contingency plans."
                )
            ],
            stop_reason="end_turn",
        ),
    ]


def orchestrator_strategy_scenario() -> list[MockResponse]:
    """Orchestrator routes to strategy, then synthesises."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "strategy",
                    {"query": "Develop a mitigation plan for the current risk exposure."},
                    tool_id="toolu_orch_strat_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    "The Strategy agent has developed a comprehensive mitigation plan.\n\n"
                    "The plan involves diversifying our supplier base and pre-positioning "
                    "safety stock. Estimated cost: $125,000 with an expected risk reduction "
                    "of 45%.\n\n"
                    "Would you like me to proceed with execution?"
                )
            ],
            stop_reason="end_turn",
        ),
    ]


def orchestrator_execution_scenario(
    order_id: str,
    new_supplier_id: str,
) -> list[MockResponse]:
    """Orchestrator routes to execution, then confirms."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "execution",
                    {
                        "query": f"Reroute order {order_id} to supplier {new_supplier_id}. User has approved."
                    },
                    tool_id="toolu_orch_exec_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    f"Done. Order {order_id} has been rerouted to supplier {new_supplier_id}. "
                    "An audit trail has been created. I'll continue monitoring the order."
                )
            ],
            stop_reason="end_turn",
        ),
    ]


def orchestrator_gate_scenario() -> list[MockResponse]:
    """Orchestrator refuses to route to execution without explicit approval."""
    return [
        MockResponse(
            content=[
                _text_block(
                    "I understand you'd like to reroute all orders from Shanghai. "
                    "Before I can execute any changes, I need to:\n\n"
                    "1. Assess the current risk exposure for Shanghai-sourced orders\n"
                    "2. Identify suitable alternative suppliers\n"
                    "3. Get your explicit approval for a specific rerouting plan\n\n"
                    "Would you like me to start with a risk assessment?"
                )
            ],
            stop_reason="end_turn",
        ),
    ]


def orchestrator_decision_log_scenario() -> list[MockResponse]:
    """Orchestrator queries the decision log."""
    return [
        MockResponse(
            content=[
                _tool_use_block(
                    "query_decision_log",
                    {"query": "recent decisions", "limit": 10},
                    tool_id="toolu_orch_log_001",
                )
            ],
            stop_reason="tool_use",
        ),
        MockResponse(
            content=[
                _text_block(
                    "Here are the recent agent decisions from the audit trail. "
                    "The decisions include rerouting actions and mitigation plans "
                    "that were executed to address supply chain disruptions."
                )
            ],
            stop_reason="end_turn",
        ),
    ]


# ---------------------------------------------------------------------------
# Multi-agent (chained) scenario
# ---------------------------------------------------------------------------


def multi_agent_scenario() -> list[MockResponse]:
    """Risk -> Simulation -> Strategy chain at the orchestrator level.

    The orchestrator makes three sequential tool calls across three
    conversation turns.
    """
    return [
        # Turn 1: route to risk_monitor
        MockResponse(
            content=[
                _tool_use_block(
                    "risk_monitor",
                    {"query": "Assess all active risk events."},
                    tool_id="toolu_multi_001",
                )
            ],
            stop_reason="tool_use",
        ),
        # Turn 2: route to simulation
        MockResponse(
            content=[
                _tool_use_block(
                    "simulation",
                    {"query": "Model the worst-case disruption scenario."},
                    tool_id="toolu_multi_002",
                )
            ],
            stop_reason="tool_use",
        ),
        # Turn 3: route to strategy
        MockResponse(
            content=[
                _tool_use_block(
                    "strategy",
                    {
                        "query": "Recommend a mitigation plan based on the risk assessment and simulation."
                    },
                    tool_id="toolu_multi_003",
                )
            ],
            stop_reason="tool_use",
        ),
        # Turn 4: synthesise everything
        MockResponse(
            content=[
                _text_block(
                    "I've completed a full analysis cycle:\n\n"
                    "1. **Risk Assessment** — Multiple active threats identified.\n"
                    "2. **Simulation** — Worst-case scenario modelled with Monte Carlo analysis.\n"
                    "3. **Strategy** — Mitigation plan developed and saved.\n\n"
                    "The recommended approach is to diversify suppliers and pre-position "
                    "safety stock. Shall I execute the plan?"
                )
            ],
            stop_reason="end_turn",
        ),
    ]
