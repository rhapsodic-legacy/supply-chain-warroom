---
description: Generate a new supply chain risk scenario with trigger event and cascading impacts.
argument-hint: <scenario_type> [--severity 1-10] [--region asia|europe|americas|global]
---

Generate a realistic supply chain disruption scenario for testing and demos.

$ARGUMENTS contains:
- scenario_type: natural_disaster, supplier_failure, logistics_disruption, demand_shock, regulatory, cyber_attack
- --severity: 1-10 (default: random 5-8)
- --region: geographic focus (default: random)

## Steps

1. Read backend/app/seed/constants.py for available ports, suppliers, and routes
2. Read backend/app/simulation/scenarios.py for existing scenario patterns
3. Generate a scenario dict with:
   - Creative but plausible name and description (vivid and specific, not generic)
   - Disruption type matching the scenario_type
   - Affected entity IDs drawn from real seed data
   - Realistic duration, severity, and parameters
   - 3-6 expected cascading impacts (first through third-order effects)
4. Add the scenario to backend/app/simulation/scenarios.py as a new preset
5. Print a human-readable summary

Make scenarios vivid: not "a port closes" but "Typhoon Meihua forces emergency closure of Ningbo-Zhoushan Port during peak shipping season, stranding 47 container vessels."
