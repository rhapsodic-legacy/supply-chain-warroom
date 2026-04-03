---
description: Scaffold a new supply chain agent with definition, tools, tests, and registration.
argument-hint: <agent_name> [--model haiku|sonnet]
---

Scaffold a new Claude Agent SDK agent for the supply chain system.

$ARGUMENTS contains the agent name in snake_case (e.g., demand_forecaster) and optional --model flag (default: sonnet).

## Steps

1. Read backend/CLAUDE.md and backend/app/agents/ to understand existing agent patterns
2. Check backend/app/agents/ for existing agents to avoid name collisions
3. Create `backend/app/agents/<agent_name>.py` with:
   - System prompt following the pattern of existing agents
   - Agent definition with model, tools, and description
   - Tool list referencing tools in backend/app/agents/tools/
4. Create tool stubs in `backend/app/agents/tools/<agent_name>_tools.py` with:
   - Tool function signatures with type hints
   - JSON schema definitions for each tool
   - Database query implementations
5. Create `backend/tests/test_<agent_name>.py` with:
   - Test that agent definition loads correctly
   - Test with mocked tool responses
   - Test structured output parsing
6. Register the agent in the orchestrator's agent definitions in `backend/app/agents/orchestrator.py`
7. Print a summary of all files created and next steps
