---
description: Trigger a supply chain simulation using a preset scenario.
argument-hint: [scenario_name] [--iterations 10000]
---

Run a supply chain disruption simulation and display results.

$ARGUMENTS contains:
- scenario_name: name of a preset scenario (optional, lists available if omitted)
- --iterations: number of Monte Carlo iterations (default: 10000)

## Steps

1. Read backend/app/simulation/scenarios.py to list available scenarios
2. If no scenario specified, list them and ask the user to pick one
3. If backend is running, call POST /api/v1/simulations/run with the scenario
4. If backend is not running, run the simulation directly via Python:
   `cd backend && python3 -c "from app.simulation.engine import run_simulation; ..."`
5. Display results:
   - Scenario description
   - Impact distribution (p50, p90, p95, p99 for cost, delay, fill rate)
   - Key findings summary
   - Comparison to baseline
