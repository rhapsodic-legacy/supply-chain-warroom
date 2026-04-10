"""Executive summary generation — boardroom-ready brief from simulation results.

Aggregates data from simulation, risk events, and agent decisions,
then generates a narrative via the three-tier LLM fallback.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import agent_service, risk_service, simulation_service
from app.services.llm_utils import ollama_generate, resolve_llm_tier

logger = logging.getLogger(__name__)


def _safe_json(raw: str | None) -> dict:
    """Parse a JSON string field, returning {} on failure."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _fmt_currency(val: float | None) -> str:
    if val is None:
        return "N/A"
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:,.1f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:,.0f}K"
    return f"${val:,.0f}"


def _fmt_pct(val: float | None) -> str:
    if val is None:
        return "N/A"
    return f"{val:+.1f}%" if val != 0 else "0.0%"


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------


async def _build_context(db: AsyncSession, sim_id: str) -> dict | None:
    """Assemble the structured data context for the summary."""
    sim = await simulation_service.get_simulation(db, sim_id)
    if sim is None or sim.status != "completed":
        return None

    baseline = _safe_json(sim.baseline_metrics)
    mitigated = _safe_json(sim.mitigated_metrics)
    comparison = _safe_json(sim.comparison)
    scenario = _safe_json(sim.scenario_params)

    # Load related data
    risk_events = await risk_service.list_risk_events(db, active_only=True)
    decisions = await agent_service.list_decisions(db, status="proposed", limit=5)
    if not decisions:
        decisions = await agent_service.list_decisions(db, limit=5)

    # Find the most relevant decision (strategy/mitigation_plan preferred)
    primary_decision = next(
        (d for d in decisions if d.decision_type == "mitigation_plan"),
        decisions[0] if decisions else None,
    )

    # ROI calculation
    mitigation_cost = abs(float(primary_decision.cost_impact or 0)) if primary_decision else 0
    params = _safe_json(
        primary_decision.parameters if primary_decision and primary_decision.parameters else None
    )
    revenue_at_risk = params.get("protected_revenue_per_day", 0)
    time_horizon = comparison.get("time_horizon_days", 90)
    cost_change_pct = comparison.get("cost_change_pct", 0)
    baseline_cost = baseline.get("total_cost", 0)
    avoided_loss = abs(cost_change_pct / 100 * baseline_cost * (time_horizon / 90)) if baseline_cost else 0

    roi_pct = ((avoided_loss - mitigation_cost) / mitigation_cost * 100) if mitigation_cost > 0 else 0
    payback_days = (mitigation_cost / revenue_at_risk) if revenue_at_risk > 0 else None

    return {
        "simulation": {
            "id": sim.id,
            "name": sim.name,
            "description": sim.description,
            "iterations": sim.iterations,
            "scenario": scenario,
            "completed_at": sim.completed_at.isoformat() if sim.completed_at else None,
        },
        "baseline": baseline,
        "mitigated": mitigated,
        "comparison": comparison,
        "risk_events": [
            {
                "title": e.title,
                "severity": e.severity,
                "severity_score": float(e.severity_score) if e.severity_score else None,
                "affected_region": e.affected_region,
                "description": e.description,
                "event_type": e.event_type,
            }
            for e in risk_events[:5]
        ],
        "decisions": [
            {
                "agent_type": d.agent_type,
                "decision_type": d.decision_type,
                "summary": d.decision_summary,
                "reasoning": d.reasoning,
                "confidence": float(d.confidence_score) if d.confidence_score else None,
                "cost_impact": float(d.cost_impact) if d.cost_impact else None,
                "time_impact_days": d.time_impact_days,
                "status": d.status,
            }
            for d in decisions
        ],
        "roi": {
            "mitigation_cost": mitigation_cost,
            "avoided_loss": avoided_loss,
            "roi_pct": roi_pct,
            "payback_days": payback_days,
            "revenue_at_risk_per_day": revenue_at_risk,
        },
    }


# ---------------------------------------------------------------------------
# Tier 3: Template-based generation (always available)
# ---------------------------------------------------------------------------


def _generate_template_summary(ctx: dict) -> dict[str, dict[str, str]]:
    """Generate structured sections using Python templates."""
    sim = ctx["simulation"]
    baseline = ctx["baseline"]
    mitigated = ctx["mitigated"]
    comp = ctx["comparison"]
    roi = ctx["roi"]
    risks = ctx["risk_events"]
    decisions = ctx["decisions"]

    # Executive Overview
    primary_risk = risks[0] if risks else None
    risk_desc = (
        f"a {primary_risk['severity']} {primary_risk['event_type']} event "
        f"— {primary_risk['title']} — disrupting operations in {primary_risk['affected_region']}"
        if primary_risk
        else "a supply chain disruption scenario"
    )

    executive_overview = (
        f"On {sim.get('completed_at', 'N/A')[:10]}, {risk_desc} was analyzed through "
        f"Monte Carlo simulation ({sim.get('iterations', 'N/A'):,} iterations). "
        f"The analysis projects a {_fmt_pct(comp.get('cost_change_pct'))} cost impact "
        f"over {comp.get('time_horizon_days', 90)} days without mitigation. "
    )
    if roi["mitigation_cost"] > 0:
        executive_overview += (
            f"The recommended mitigation plan costs {_fmt_currency(roi['mitigation_cost'])} "
            f"with an estimated ROI of {roi['roi_pct']:.0f}%."
        )

    # Disruption Summary
    disruption_lines = []
    for r in risks:
        disruption_lines.append(
            f"**{r['title']}** ({r['severity'].upper()}, score: {r.get('severity_score', 'N/A')})"
            f"\n  Region: {r.get('affected_region', 'N/A')}"
            f"\n  {r['description']}"
        )
    disruption_summary = "\n\n".join(disruption_lines) if disruption_lines else "No active risk events."

    # Monte Carlo Results
    mc_results = (
        f"**Iterations:** {sim.get('iterations', 'N/A'):,} | "
        f"**Time horizon:** {comp.get('time_horizon_days', 90)} days\n\n"
        f"| Metric | Baseline | Disrupted | Change |\n"
        f"|--------|----------|-----------|--------|\n"
        f"| Total Cost | {_fmt_currency(baseline.get('total_cost'))} | "
        f"{_fmt_currency(mitigated.get('total_cost'))} | "
        f"{_fmt_pct(comp.get('cost_change_pct'))} |\n"
        f"| Fill Rate | {baseline.get('fill_rate', 'N/A'):.1%} | "
        f"{mitigated.get('fill_rate', 'N/A'):.1%} | "
        f"{comp.get('fill_rate_change', 0):+.1%} |\n"
        f"| Avg Lead Time | {baseline.get('avg_lead_time', 'N/A'):.1f}d | "
        f"{mitigated.get('avg_lead_time', 'N/A'):.1f}d | "
        f"{comp.get('delay_change_days', 0):+.1f}d |\n\n"
        f"**P95 Cost:** {_fmt_currency(comp.get('cost_p95'))} | "
        f"**P95 Delay:** {comp.get('delay_p95', 'N/A')}d | "
        f"**Mean Stockouts:** {comp.get('stockout_mean', 'N/A')}"
    )

    # Agent Recommendations
    rec_lines = []
    for d in decisions:
        conf_str = f"{d['confidence']:.0%}" if d["confidence"] else "N/A"
        cost_str = _fmt_currency(d["cost_impact"]) if d["cost_impact"] else "N/A"
        rec_lines.append(
            f"**{d['agent_type'].replace('_', ' ').title()}** — {d['summary']}\n"
            f"  Confidence: {conf_str} | Cost impact: {cost_str} | Status: {d['status']}"
        )
    agent_recommendations = "\n\n".join(rec_lines) if rec_lines else "No agent recommendations available."

    # ROI Analysis
    roi_analysis = (
        f"| Metric | Value |\n"
        f"|--------|-------|\n"
        f"| Mitigation Cost | {_fmt_currency(roi['mitigation_cost'])} |\n"
        f"| Avoided Loss (projected) | {_fmt_currency(roi['avoided_loss'])} |\n"
        f"| Net ROI | {roi['roi_pct']:.0f}% |\n"
        f"| Payback Period | {roi['payback_days']:.1f} days |\n"
        f"| Revenue at Risk/Day | {_fmt_currency(roi['revenue_at_risk_per_day'])} |"
        if roi["mitigation_cost"] > 0
        else "No mitigation cost data available for ROI calculation."
    )

    # Risk Matrix
    matrix_lines = ["| Event | Severity | Score | Region |", "|-------|----------|-------|--------|"]
    for r in risks:
        score = f"{r.get('severity_score', 'N/A')}" if r.get("severity_score") else "N/A"
        matrix_lines.append(
            f"| {r['title'][:40]} | {r['severity'].upper()} | {score} | {r.get('affected_region', 'N/A')} |"
        )
    risk_matrix = "\n".join(matrix_lines) if len(matrix_lines) > 2 else "No active risk events."

    return {
        "executive_overview": {"title": "Executive Overview", "content": executive_overview},
        "disruption_summary": {"title": "Disruption Summary", "content": disruption_summary},
        "monte_carlo_results": {"title": "Monte Carlo Analysis", "content": mc_results},
        "agent_recommendations": {"title": "Agent Recommendations", "content": agent_recommendations},
        "roi_analysis": {"title": "ROI Analysis", "content": roi_analysis},
        "risk_matrix": {"title": "Risk Matrix", "content": risk_matrix},
    }


# ---------------------------------------------------------------------------
# Tier 1/2: LLM-enhanced generation
# ---------------------------------------------------------------------------

_SUMMARY_SYSTEM_PROMPT = """\
You are a supply chain executive briefing writer. Generate a concise, data-driven
executive summary from the provided analysis data. Use the exact numbers from the data.

Structure your response as JSON with these keys:
- executive_overview: 2-3 sentence high-level summary for C-suite
- disruption_summary: What happened, severity, affected regions
- monte_carlo_results: Key metrics from the simulation (use the actual numbers provided)
- agent_recommendations: What the AI agents recommend and why
- roi_analysis: Cost-benefit breakdown of the mitigation plan
- risk_matrix: Current risk landscape overview

Each value should be a markdown-formatted string. Be precise with numbers.
Keep the total under 800 words. Tone: professional, concise, data-forward.
"""


async def _generate_llm_summary(
    ctx: dict, tier: str
) -> dict[str, dict[str, str]] | None:
    """Generate summary sections via Claude or Gemma."""
    context_str = json.dumps(ctx, indent=2, default=str)

    if tier == "claude":
        try:
            import anthropic

            client = anthropic.AsyncAnthropic()
            resp = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                system=_SUMMARY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"Generate the executive brief from this data:\n\n{context_str}"}],
            )
            text = resp.content[0].text
        except Exception:
            logger.exception("Claude executive summary generation failed")
            return None

    elif tier == "gemma":
        prompt = (
            f"{_SUMMARY_SYSTEM_PROMPT}\n\n"
            f"Data:\n{context_str[:2000]}\n\n"
            f"Generate the JSON response:"
        )
        try:
            text = await ollama_generate(prompt, max_tokens=800)
        except Exception:
            logger.exception("Gemma executive summary generation failed")
            return None
    else:
        return None

    # Parse the LLM JSON response
    try:
        # Extract JSON from potential markdown code blocks
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        parsed = json.loads(text.strip())
        section_titles = {
            "executive_overview": "Executive Overview",
            "disruption_summary": "Disruption Summary",
            "monte_carlo_results": "Monte Carlo Analysis",
            "agent_recommendations": "Agent Recommendations",
            "roi_analysis": "ROI Analysis",
            "risk_matrix": "Risk Matrix",
        }
        return {
            key: {"title": section_titles.get(key, key), "content": str(parsed.get(key, ""))}
            for key in section_titles
        }
    except (json.JSONDecodeError, IndexError, KeyError):
        logger.warning("Failed to parse LLM summary response, falling back to template")
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def generate_summary(db: AsyncSession, sim_id: str) -> dict | None:
    """Generate an executive summary for a completed simulation.

    Returns None if the simulation doesn't exist or isn't completed.
    """
    ctx = await _build_context(db, sim_id)
    if ctx is None:
        return None

    tier = await resolve_llm_tier()
    sections = None

    # Try LLM tiers first
    if tier in ("claude", "gemma"):
        sections = await _generate_llm_summary(ctx, tier)

    # Fall back to template
    if sections is None:
        tier = "template"
        sections = _generate_template_summary(ctx)

    return {
        "simulation_id": sim_id,
        "simulation_name": ctx["simulation"]["name"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_tier": tier,
        "sections": sections,
        "raw_metrics": {
            "baseline": ctx["baseline"],
            "mitigated": ctx["mitigated"],
            "comparison": ctx["comparison"],
            "roi": ctx["roi"],
        },
    }
