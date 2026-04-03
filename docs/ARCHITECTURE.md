# Architecture — Supply Chain War Room

## System Overview

The Supply Chain War Room is a multi-agent AI system built on a hub-and-spoke architecture. An Orchestrator agent receives all user interactions and dispatches to four specialist agents, each with domain-specific tools and system prompts.

## Data Flow

1. **Risk events** enter the system (via seed data, manual creation, or simulation)
2. The **Orchestrator** receives user queries and routes to the appropriate specialist agent
3. **Risk Monitor** detects and scores threats using database queries and composite scoring
4. **Simulation Agent** triggers the Monte Carlo engine for what-if scenarios
5. **Strategy Agent** analyzes results and generates mitigation plans with cost-benefit analysis
6. **Execution Agent** carries out approved actions: reroutes orders, triggers safety stock, logs webhooks
7. All decisions are logged to the **audit trail** and streamed to the **dashboard via SSE**

## Agent Communication

Agents never communicate directly with each other. All inter-agent coordination flows through the Orchestrator, which chains agents sequentially when a multi-step workflow is needed (e.g., "Simulate X and recommend a strategy").

## Database Schema

11 tables across 4 domains:

**Supply Chain:** suppliers, products, supplier_products, shipping_routes, orders, order_events
**Demand:** demand_signals
**Risk:** risk_events, risk_event_impacts
**AI:** agent_decisions, simulations

## Simulation Engine

Pure NumPy computation. Models the supply chain as a directed weighted graph. Uses log-normal distributions for lead times, Poisson for demand variation, and Bernoulli for reliability failures. 10K iterations complete in <0.2 seconds.

## Real-time Updates

Server-Sent Events (SSE) push risk events, agent decisions, and order updates to the frontend. The frontend uses TanStack Query for data fetching with automatic invalidation on SSE events.
