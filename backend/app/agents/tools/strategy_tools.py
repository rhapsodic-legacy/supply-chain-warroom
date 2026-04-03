"""Tool implementations for the Strategy agent.

Functions for evaluating inventory, finding alternative suppliers,
generating mitigation plans, and running cost-benefit analyses.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentDecision,
    Order,
    Product,
    Supplier,
    SupplierProduct,
)


async def query_inventory_status(db: AsyncSession) -> str:
    """Return current order quantities grouped by product and order status."""
    stmt = (
        select(
            Product.id,
            Product.name,
            Product.sku,
            Product.is_critical,
            Order.status,
            func.count(Order.id).label("order_count"),
            func.sum(Order.quantity).label("total_qty"),
            func.sum(Order.total_cost).label("total_cost"),
        )
        .join(Order, Order.product_id == Product.id)
        .group_by(Product.id, Product.name, Product.sku, Product.is_critical, Order.status)
        .order_by(Product.name, Order.status)
    )
    result = await db.execute(stmt)
    rows = result.all()

    inventory = []
    for row in rows:
        inventory.append(
            {
                "product_id": row.id,
                "product_name": row.name,
                "sku": row.sku,
                "is_critical": row.is_critical,
                "status": row.status,
                "order_count": row.order_count,
                "total_qty": int(row.total_qty or 0),
                "total_cost_usd": round(float(row.total_cost or 0), 2),
            }
        )
    return json.dumps(inventory, default=str)


async def query_alternative_suppliers(
    db: AsyncSession,
    product_id: str,
    exclude_supplier_id: str | None = None,
) -> str:
    """Find alternative suppliers for a given product, ranked by reliability and cost."""
    stmt = (
        select(
            Supplier.id,
            Supplier.name,
            Supplier.country,
            Supplier.region,
            Supplier.reliability_score,
            Supplier.base_lead_time_days,
            Supplier.cost_multiplier,
            Supplier.capacity_units,
            SupplierProduct.unit_price,
            SupplierProduct.min_order_qty,
        )
        .join(SupplierProduct, SupplierProduct.supplier_id == Supplier.id)
        .where(SupplierProduct.product_id == product_id)
        .where(Supplier.is_active.is_(True))
    )

    if exclude_supplier_id:
        stmt = stmt.where(Supplier.id != exclude_supplier_id)

    stmt = stmt.order_by(Supplier.reliability_score.desc())
    result = await db.execute(stmt)
    rows = result.all()

    alternatives = []
    for row in rows:
        alternatives.append(
            {
                "supplier_id": row.id,
                "supplier_name": row.name,
                "country": row.country,
                "region": row.region,
                "reliability_score": float(row.reliability_score),
                "base_lead_time_days": row.base_lead_time_days,
                "cost_multiplier": float(row.cost_multiplier),
                "capacity_units": row.capacity_units,
                "unit_price": float(row.unit_price),
                "min_order_qty": row.min_order_qty,
            }
        )

    return json.dumps(alternatives, default=str)


async def generate_mitigation_plan(
    db: AsyncSession,
    risk_event_id: str | None,
    strategy_description: str,
    actions_json: str,
    estimated_cost: float,
    risk_reduction_pct: float,
) -> str:
    """Write a proposed mitigation plan as an AgentDecision record.

    The plan is saved with status='proposed' for user review before execution.
    """
    decision = AgentDecision(
        id=str(uuid.uuid4()),
        agent_type="strategy",
        trigger_event_id=risk_event_id,
        decision_type="mitigation_plan",
        decision_summary=strategy_description,
        reasoning=actions_json,
        confidence_score=min(risk_reduction_pct / 100.0, 1.0),
        affected_orders="[]",
        parameters=json.dumps(
            {
                "actions": actions_json,
                "estimated_cost_usd": estimated_cost,
                "risk_reduction_pct": risk_reduction_pct,
            }
        ),
        status="proposed",
        cost_impact=estimated_cost,
        decided_at=datetime.utcnow(),
    )
    db.add(decision)
    await db.commit()
    await db.refresh(decision)

    return json.dumps(
        {
            "status": "proposed",
            "decision_id": decision.id,
            "summary": strategy_description,
            "estimated_cost_usd": estimated_cost,
            "risk_reduction_pct": risk_reduction_pct,
            "message": "Mitigation plan saved. Awaiting user approval before execution.",
        }
    )


async def cost_benefit_analysis(
    db: AsyncSession,
    current_cost: float,
    proposed_cost: float,
    delay_reduction_days: float,
    risk_reduction_pct: float,
) -> str:
    """Compute a structured cost-benefit analysis for a proposed strategy change."""
    cost_delta = proposed_cost - current_cost
    cost_change_pct = (cost_delta / max(current_cost, 1)) * 100

    # Simple value-of-time model: each day of delay reduction is worth
    # roughly 2% of order value in avoided carrying / stockout costs
    delay_value = delay_reduction_days * current_cost * 0.02
    risk_value = (risk_reduction_pct / 100) * current_cost * 0.15

    net_benefit = delay_value + risk_value - cost_delta
    roi = (net_benefit / max(abs(cost_delta), 1)) * 100 if cost_delta != 0 else float("inf")

    recommendation = (
        "RECOMMENDED" if net_benefit > 0 else "NOT RECOMMENDED"
    )

    analysis = {
        "current_cost_usd": round(current_cost, 2),
        "proposed_cost_usd": round(proposed_cost, 2),
        "cost_delta_usd": round(cost_delta, 2),
        "cost_change_pct": round(cost_change_pct, 2),
        "delay_reduction_days": round(delay_reduction_days, 1),
        "delay_value_usd": round(delay_value, 2),
        "risk_reduction_pct": round(risk_reduction_pct, 1),
        "risk_value_usd": round(risk_value, 2),
        "net_benefit_usd": round(net_benefit, 2),
        "roi_pct": round(roi, 2) if roi != float("inf") else "infinite",
        "recommendation": recommendation,
    }
    return json.dumps(analysis)
