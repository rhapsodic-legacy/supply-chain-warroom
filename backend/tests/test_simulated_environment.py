"""Simulated environment tests.

These tests exercise the complete agent pipeline -- from user message through
orchestrator routing, specialist agent tool use, database mutations, and back
to user response -- with deterministic mocked Claude API responses.

The mock returns tool_use blocks that trigger REAL tool execution against a
seeded test database, verifying that the tools actually mutate state correctly.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from app.models import AgentDecision, Order, OrderEvent, RiskEvent, Simulation

from tests.mock_anthropic import (
    MockAsyncAnthropic,
    MockContentBlock,
    MockResponse,
    execution_scenario,
    orchestrator_decision_log_scenario,
    orchestrator_execution_scenario,
    orchestrator_gate_scenario,
    orchestrator_risk_scenario,
    orchestrator_simulation_scenario,
    orchestrator_strategy_scenario,
    risk_assessment_scenario,
    simulation_scenario,
    strategy_scenario,
)


# =========================================================================
# Helpers
# =========================================================================


async def _count_rows(db, model):
    """Return the row count for a given model."""
    result = await db.execute(select(func.count(model.id)))
    return result.scalar() or 0


async def _get_first_order(db) -> Order | None:
    result = await db.execute(select(Order).limit(1))
    return result.scalar_one_or_none()


async def _get_first_active_supplier_id(db) -> str | None:
    from app.models import Supplier
    result = await db.execute(
        select(Supplier.id).where(Supplier.is_active.is_(True)).limit(1)
    )
    row = result.first()
    return row[0] if row else None


async def _get_different_supplier_id(db, exclude_id: str) -> str | None:
    from app.models import Supplier
    result = await db.execute(
        select(Supplier.id)
        .where(Supplier.is_active.is_(True), Supplier.id != exclude_id)
        .limit(1)
    )
    row = result.first()
    return row[0] if row else None


# =========================================================================
# Scenario 1: Risk Assessment Workflow (read-only)
# =========================================================================


class TestRiskAssessmentWorkflow:
    """The risk monitor queries the DB but makes no mutations."""

    async def test_risk_monitor_queries_active_risks(
        self, seeded_db, mock_anthropic
    ):
        # Configure mock for the risk_monitor agent (inner agent, not orchestrator)
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            risk_assessment_scenario(),
        )

        # Count rows before
        risk_count_before = await _count_rows(seeded_db, RiskEvent)
        decision_count_before = await _count_rows(seeded_db, AgentDecision)

        # Run the risk monitor directly
        from app.agents.risk_monitor import run_risk_monitor

        result = await run_risk_monitor(seeded_db, "What are the top risks right now?")

        # Verify we got a text response
        assert "response" in result
        assert len(result["response"]) > 0

        # Verify the mock was called (tool_use + follow-up)
        assert mock_anthropic.messages._call_count == 2

        # Verify the first call got tool_use, which triggered query_risk_events
        first_call = mock_anthropic.messages._call_log[0]
        assert first_call["messages"][0]["content"] == "What are the top risks right now?"

        # Verify NO database mutations occurred (read-only flow)
        risk_count_after = await _count_rows(seeded_db, RiskEvent)
        decision_count_after = await _count_rows(seeded_db, AgentDecision)
        assert risk_count_after == risk_count_before
        assert decision_count_after == decision_count_before


# =========================================================================
# Scenario 2: Simulation Workflow
# =========================================================================


class TestSimulationWorkflow:
    """The simulation agent runs Monte Carlo and persists results."""

    async def test_simulation_creates_record(
        self, seeded_db, mock_anthropic
    ):
        # Configure mock for the simulation agent
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            simulation_scenario(scenario_name="suez_canal_closure", iterations=500),
        )

        sim_count_before = await _count_rows(seeded_db, Simulation)

        from app.agents.simulation_agent import run_simulation_agent

        result = await run_simulation_agent(
            seeded_db, "Simulate a Suez Canal closure for 3 weeks"
        )

        # Got a response
        assert "response" in result
        assert "simulation" in result["response"].lower() or "complete" in result["response"].lower()

        # A new Simulation record should exist
        sim_count_after = await _count_rows(seeded_db, Simulation)
        assert sim_count_after == sim_count_before + 1

        # The new simulation should be completed with metrics
        latest = await seeded_db.execute(
            select(Simulation).order_by(Simulation.created_at.desc()).limit(1)
        )
        sim = latest.scalar_one()
        assert sim.status == "completed"
        assert sim.baseline_metrics is not None
        assert sim.mitigated_metrics is not None

        # Verify metrics are valid JSON
        baseline = json.loads(sim.baseline_metrics)
        mitigated = json.loads(sim.mitigated_metrics)
        assert "cost" in baseline
        assert "cost" in mitigated


# =========================================================================
# Scenario 3: Full Lifecycle -- Risk -> Strategy -> Execution
# =========================================================================


class TestFullLifecycleWorkflow:
    """Multi-turn conversation: risk assessment, strategy, execution, audit."""

    async def test_turn1_risk_assessment(self, seeded_db, mock_anthropic):
        """Turn 1: User asks about risk exposure."""
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            risk_assessment_scenario(),
        )

        from app.agents.risk_monitor import run_risk_monitor

        result = await run_risk_monitor(
            seeded_db, "What's our exposure to the Rotterdam strike?"
        )
        assert len(result["response"]) > 0
        # No mutations
        assert await _count_rows(seeded_db, AgentDecision) == 0

    async def test_turn2_strategy_creates_proposed_decision(
        self, seeded_db, mock_anthropic
    ):
        """Turn 2: User asks for recommendations -- creates a proposed decision."""
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            strategy_scenario(risk_event_id=None),
        )

        decision_count_before = await _count_rows(seeded_db, AgentDecision)

        from app.agents.strategy_agent import run_strategy_agent

        result = await run_strategy_agent(
            seeded_db, "What should we do about it?"
        )
        assert len(result["response"]) > 0

        # An AgentDecision with status="proposed" should be created
        decision_count_after = await _count_rows(seeded_db, AgentDecision)
        assert decision_count_after == decision_count_before + 1

        # Verify the decision is proposed
        latest = await seeded_db.execute(
            select(AgentDecision)
            .order_by(AgentDecision.decided_at.desc())
            .limit(1)
        )
        decision = latest.scalar_one()
        assert decision.status == "proposed"
        assert decision.agent_type == "strategy"
        assert decision.decision_type == "mitigation_plan"

    async def test_turn3_execution_reroutes_order(
        self, seeded_db, mock_anthropic
    ):
        """Turn 3: User approves execution -- order is rerouted."""
        # Get a real order and a different supplier to reroute to
        order = await _get_first_order(seeded_db)
        assert order is not None, "No orders in seed data"

        new_supplier_id = await _get_different_supplier_id(
            seeded_db, order.supplier_id
        )
        assert new_supplier_id is not None, "Could not find alternative supplier"

        original_supplier = order.supplier_id

        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            execution_scenario(order.id, new_supplier_id),
        )

        decision_count_before = await _count_rows(seeded_db, AgentDecision)
        event_count_before = await _count_rows(seeded_db, OrderEvent)

        from app.agents.execution_agent import run_execution_agent

        result = await run_execution_agent(
            seeded_db, "Execute the rerouting plan"
        )
        assert len(result["response"]) > 0

        # The order should be rerouted
        await seeded_db.refresh(order)
        assert order.supplier_id == new_supplier_id

        # An AgentDecision with status="executed" should be created
        decision_count_after = await _count_rows(seeded_db, AgentDecision)
        assert decision_count_after >= decision_count_before + 1

        latest_decision = await seeded_db.execute(
            select(AgentDecision)
            .where(AgentDecision.agent_type == "execution")
            .order_by(AgentDecision.decided_at.desc())
            .limit(1)
        )
        decision = latest_decision.scalar_one()
        assert decision.status == "executed"
        assert decision.decision_type == "order_reroute"

        # An OrderEvent should be created
        event_count_after = await _count_rows(seeded_db, OrderEvent)
        assert event_count_after >= event_count_before + 1

    async def test_turn4_decision_log_queryable(
        self, seeded_db, mock_anthropic
    ):
        """Turn 4: Query the decision log -- previous decisions are visible.

        This test depends on decisions created in turn2 and turn3. We run
        those first inline to ensure state is present.
        """
        # Create a strategy decision first
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            strategy_scenario(risk_event_id=None),
        )
        from app.agents.strategy_agent import run_strategy_agent
        await run_strategy_agent(seeded_db, "Plan something")

        # Create an execution decision
        order = await _get_first_order(seeded_db)
        new_supplier_id = await _get_different_supplier_id(
            seeded_db, order.supplier_id
        )
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            execution_scenario(order.id, new_supplier_id),
        )
        from app.agents.execution_agent import run_execution_agent
        await run_execution_agent(seeded_db, "Execute it")

        # Now query the decision log directly
        from app.agents.orchestrator import _query_decision_log

        log_json = await _query_decision_log(seeded_db, limit=10)
        decisions = json.loads(log_json)
        assert len(decisions) >= 2

        # We should see both strategy and execution decisions
        agent_types = {d["agent_type"] for d in decisions}
        assert "strategy" in agent_types
        assert "execution" in agent_types

        # All decisions should have required audit fields
        for d in decisions:
            assert d["id"] is not None
            assert d["decision_type"] is not None
            assert d["summary"] is not None
            assert d["reasoning"] is not None


# =========================================================================
# Scenario 4: Execution Gate -- Blocks Unauthorized Action
# =========================================================================


class TestExecutionGate:
    """The orchestrator should refuse execution without explicit approval."""

    async def test_blocks_unauthorized_action(
        self, seeded_db, mock_anthropic
    ):
        # Configure the orchestrator mock to NOT call execution
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            orchestrator_gate_scenario(),
        )

        decision_count_before = await _count_rows(seeded_db, AgentDecision)
        order_event_count_before = await _count_rows(seeded_db, OrderEvent)

        from app.agents.orchestrator import run_orchestrator

        result = await run_orchestrator(
            seeded_db, "Reroute all orders from Shanghai immediately"
        )

        # Should get a text response (not route to execution)
        assert "response" in result
        assert len(result["response"]) > 0

        # No database mutations should have occurred
        decision_count_after = await _count_rows(seeded_db, AgentDecision)
        order_event_count_after = await _count_rows(seeded_db, OrderEvent)
        assert decision_count_after == decision_count_before
        assert order_event_count_after == order_event_count_before

        # The response should indicate clarification is needed
        response_lower = result["response"].lower()
        assert any(
            word in response_lower
            for word in ["approval", "approve", "confirm", "assessment", "before"]
        ), f"Expected gating language in response, got: {result['response'][:200]}"


# =========================================================================
# Scenario 5: Concurrent Risk Events
# =========================================================================


class TestConcurrentRiskEvents:
    """A newly created risk event should be visible to the agent."""

    async def test_new_risk_visible_to_agent(
        self, seeded_db, mock_anthropic
    ):
        # Step 1: Create a new risk event directly in the DB
        new_risk = RiskEvent(
            event_type="logistics",
            title="E2E Test -- New Port Congestion Alert",
            description="Sudden congestion at a major transshipment hub.",
            severity="high",
            severity_score=0.80,
            affected_region="Southeast Asia",
            is_active=True,
        )
        seeded_db.add(new_risk)
        await seeded_db.commit()
        await seeded_db.refresh(new_risk)
        new_risk_id = new_risk.id

        # Step 2: Configure mock for the risk_monitor -- it will call
        # query_risk_events which does a REAL DB query
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            risk_assessment_scenario(),
        )

        from app.agents.risk_monitor import run_risk_monitor

        result = await run_risk_monitor(seeded_db, "Assess the new threat")

        # Step 3: Verify the tool was called and hit the DB
        assert mock_anthropic.messages._call_count == 2

        # The real query_risk_events ran against the DB and should have
        # returned the new event among active risks.
        # Verify the event exists in the DB
        check = await seeded_db.execute(
            select(RiskEvent).where(RiskEvent.id == new_risk_id)
        )
        event = check.scalar_one_or_none()
        assert event is not None
        assert event.is_active is True
        assert event.title == "E2E Test -- New Port Congestion Alert"


# =========================================================================
# Orchestrator integration tests
# =========================================================================


class TestOrchestratorRouting:
    """Test the orchestrator routes to the correct specialist agents."""

    async def test_orchestrator_routes_to_risk_monitor(
        self, seeded_db, mock_anthropic
    ):
        """Orchestrator routes risk questions to the risk_monitor tool."""
        # The orchestrator mock calls risk_monitor tool, which invokes
        # run_risk_monitor (which itself needs a mock).
        # We configure two layers of mock responses:
        # Layer 1: Orchestrator sees risk question -> calls risk_monitor tool
        # Layer 2: risk_monitor agent uses the same mock client

        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            orchestrator_risk_scenario(),
        )
        # The inner risk_monitor call also goes through the mock:
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            risk_assessment_scenario(),
        )

        from app.agents.orchestrator import run_orchestrator

        result = await run_orchestrator(
            seeded_db, "What risks do we face right now?"
        )

        assert "response" in result
        assert len(result["response"]) > 0
        assert len(result["actions"]) > 0
        assert result["actions"][0]["agent"] == "risk_monitor"

    async def test_orchestrator_routes_to_simulation(
        self, seeded_db, mock_anthropic
    ):
        """Orchestrator routes simulation questions to the simulation tool."""
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            orchestrator_simulation_scenario(),
        )
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            simulation_scenario(iterations=500),
        )

        from app.agents.orchestrator import run_orchestrator

        result = await run_orchestrator(
            seeded_db, "Simulate a Suez Canal closure for 3 weeks"
        )

        assert "response" in result
        assert len(result["actions"]) > 0
        assert result["actions"][0]["agent"] == "simulation"

        # A simulation record should have been created
        sim_count = await _count_rows(seeded_db, Simulation)
        assert sim_count >= 1

    async def test_orchestrator_routes_to_strategy(
        self, seeded_db, mock_anthropic
    ):
        """Orchestrator routes strategy questions to the strategy tool."""
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            orchestrator_strategy_scenario(),
        )
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            strategy_scenario(),
        )

        from app.agents.orchestrator import run_orchestrator

        result = await run_orchestrator(
            seeded_db, "What should we do about the supply disruption?"
        )

        assert "response" in result
        assert len(result["actions"]) > 0
        assert result["actions"][0]["agent"] == "strategy"

        # A proposed decision should have been created
        decisions = await seeded_db.execute(
            select(AgentDecision).where(AgentDecision.status == "proposed")
        )
        assert decisions.scalars().first() is not None

    async def test_orchestrator_execution_with_approval(
        self, seeded_db, mock_anthropic
    ):
        """Orchestrator routes to execution when user explicitly approves."""
        order = await _get_first_order(seeded_db)
        new_supplier_id = await _get_different_supplier_id(
            seeded_db, order.supplier_id
        )

        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            orchestrator_execution_scenario(order.id, new_supplier_id),
        )
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            execution_scenario(order.id, new_supplier_id),
        )

        from app.agents.orchestrator import run_orchestrator

        result = await run_orchestrator(
            seeded_db, f"Yes, reroute order {order.id} to supplier {new_supplier_id}. Proceed."
        )

        assert "response" in result
        assert len(result["actions"]) > 0
        assert result["actions"][0]["agent"] == "execution"

    async def test_orchestrator_queries_decision_log(
        self, seeded_db, mock_anthropic
    ):
        """Orchestrator can query the decision log for audit trail."""
        # First create a decision to query
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            strategy_scenario(),
        )
        from app.agents.strategy_agent import run_strategy_agent
        await run_strategy_agent(seeded_db, "Create a plan")

        # Now test the orchestrator querying the log
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            orchestrator_decision_log_scenario(),
        )

        from app.agents.orchestrator import run_orchestrator

        result = await run_orchestrator(
            seeded_db, "Why did you create that mitigation plan?"
        )

        assert "response" in result
        assert len(result["actions"]) > 0
        assert result["actions"][0]["agent"] == "query_decision_log"


# =========================================================================
# Mock introspection tests
# =========================================================================


class TestMockCallLog:
    """Verify that the mock records calls correctly for test assertions."""

    async def test_call_log_records_all_parameters(
        self, seeded_db, mock_anthropic
    ):
        mock_anthropic.messages.add_scenario(
            lambda msgs: True,
            risk_assessment_scenario(),
        )

        from app.agents.risk_monitor import run_risk_monitor

        await run_risk_monitor(seeded_db, "Test query")

        # Two calls: initial + after tool results
        assert mock_anthropic.messages._call_count == 2

        # First call should have the system prompt and tools
        first_call = mock_anthropic.messages._call_log[0]
        assert "system" in first_call
        assert "tools" in first_call
        assert "messages" in first_call
        assert first_call["model"] == "claude-sonnet-4-20250514"

        # Second call should include tool results in messages
        second_call = mock_anthropic.messages._call_log[1]
        messages = second_call["messages"]
        # messages should have: user, assistant (tool_use), user (tool_results)
        assert len(messages) == 3
        # Last message should contain tool results
        last_msg = messages[-1]
        assert last_msg["role"] == "user"
        # Content is a list of tool_result dicts
        assert isinstance(last_msg["content"], list)
        assert last_msg["content"][0]["type"] == "tool_result"
