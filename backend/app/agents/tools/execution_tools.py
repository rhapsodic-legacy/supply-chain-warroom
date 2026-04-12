"""Tool implementations for the Execution agent.

Every function that modifies state creates an AgentDecision audit record.
These tools carry out approved actions on orders, suppliers, and inventory.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentDecision,
    Order,
    OrderEvent,
    Product,
    ShippingRoute,
    Supplier,
    SupplierProduct,
)


async def reroute_order(
    db: AsyncSession,
    order_id: str,
    new_supplier_id: str | None = None,
    new_route_id: str | None = None,
    reason: str | None = None,
) -> str:
    """Reroute an existing order to a different supplier and/or shipping route.

    Creates an OrderEvent and an AgentDecision audit record.
    """
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        return json.dumps({"error": f"Order {order_id} not found."})

    old_supplier_id = order.supplier_id
    old_route_id = order.route_id
    changes: dict[str, str] = {}

    if new_supplier_id:
        # Verify supplier exists and is active
        sup_result = await db.execute(
            select(Supplier).where(Supplier.id == new_supplier_id, Supplier.is_active.is_(True))
        )
        new_supplier = sup_result.scalar_one_or_none()
        if not new_supplier:
            return json.dumps({"error": f"Supplier {new_supplier_id} not found or inactive."})
        order.supplier_id = new_supplier_id
        changes["supplier"] = f"{old_supplier_id} -> {new_supplier_id}"

    if new_route_id:
        route_result = await db.execute(
            select(ShippingRoute).where(
                ShippingRoute.id == new_route_id, ShippingRoute.is_active.is_(True)
            )
        )
        new_route = route_result.scalar_one_or_none()
        if not new_route:
            return json.dumps({"error": f"Route {new_route_id} not found or inactive."})
        order.route_id = new_route_id
        changes["route"] = f"{old_route_id} -> {new_route_id}"

    if not changes:
        return json.dumps(
            {"error": "No changes specified. Provide new_supplier_id or new_route_id."}
        )

    # Create order event
    event = OrderEvent(
        id=str(uuid.uuid4()),
        order_id=order_id,
        event_type="reroute",
        old_value=json.dumps({"supplier_id": old_supplier_id, "route_id": old_route_id}),
        new_value=json.dumps({"supplier_id": order.supplier_id, "route_id": order.route_id}),
        agent_id="execution_agent",
    )
    db.add(event)

    # Audit record
    decision = AgentDecision(
        id=str(uuid.uuid4()),
        agent_type="execution",
        decision_type="order_reroute",
        decision_summary=f"Rerouted order {order.order_number}: {reason or 'Agent-initiated reroute'}",
        reasoning=reason or "Reroute executed by Execution agent upon user approval.",
        confidence_score=0.90,
        affected_orders=json.dumps([order_id]),
        parameters=json.dumps(changes),
        status="executed",
        decided_at=datetime.utcnow(),
        executed_at=datetime.utcnow(),
    )
    db.add(decision)

    await db.commit()

    from app.routers.stream import publish_event

    await publish_event(
        "agent_action",
        {
            "action": f"Rerouted order {order.order_number}",
            "agent_type": "execution",
            "decision_type": "order_reroute",
            "decision_id": decision.id,
            "confidence": 0.90,
        },
    )

    return json.dumps(
        {
            "status": "rerouted",
            "order_id": order_id,
            "order_number": order.order_number,
            "changes": changes,
            "decision_id": decision.id,
            "reason": reason,
        }
    )


async def trigger_safety_stock(
    db: AsyncSession,
    product_id: str,
    quantity: int,
    urgency: str,
    reason: str,
) -> str:
    """Create an emergency safety-stock order for a product.

    Selects the most reliable active supplier for the product and places
    an expedited order.
    """
    # Find product
    prod_result = await db.execute(select(Product).where(Product.id == product_id))
    product = prod_result.scalar_one_or_none()
    if not product:
        return json.dumps({"error": f"Product {product_id} not found."})

    # Find best supplier for this product
    supplier_stmt = (
        select(Supplier, SupplierProduct.unit_price)
        .join(SupplierProduct, SupplierProduct.supplier_id == Supplier.id)
        .where(SupplierProduct.product_id == product_id)
        .where(Supplier.is_active.is_(True))
        .order_by(Supplier.reliability_score.desc())
        .limit(1)
    )
    sup_result = await db.execute(supplier_stmt)
    row = sup_result.first()
    if not row:
        return json.dumps({"error": f"No active supplier found for product {product_id}."})

    supplier, unit_price = row
    total_cost = float(unit_price) * quantity

    # Determine lead time based on urgency
    lead_time_multiplier = {"critical": 0.5, "high": 0.7, "medium": 1.0, "low": 1.2}
    adjusted_lead_time = int(supplier.base_lead_time_days * lead_time_multiplier.get(urgency, 1.0))

    # Generate order number
    order_number = f"EMG-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

    order = Order(
        id=str(uuid.uuid4()),
        order_number=order_number,
        product_id=product_id,
        supplier_id=supplier.id,
        quantity=quantity,
        unit_price=float(unit_price),
        total_cost=total_cost,
        status="pending",
        ordered_at=datetime.utcnow(),
        expected_delivery=datetime.utcnow() + timedelta(days=adjusted_lead_time),
    )
    db.add(order)

    # Audit record
    decision = AgentDecision(
        id=str(uuid.uuid4()),
        agent_type="execution",
        decision_type="safety_stock_order",
        decision_summary=f"Emergency order {order_number}: {quantity} units of {product.name} ({urgency} urgency)",
        reasoning=reason,
        confidence_score=0.85,
        affected_orders=json.dumps([order.id]),
        parameters=json.dumps(
            {
                "product_id": product_id,
                "product_name": product.name,
                "quantity": quantity,
                "urgency": urgency,
                "supplier_id": supplier.id,
                "supplier_name": supplier.name,
                "unit_price": float(unit_price),
                "total_cost": total_cost,
                "expected_lead_time_days": adjusted_lead_time,
            }
        ),
        status="executed",
        cost_impact=total_cost,
        time_impact_days=adjusted_lead_time,
        decided_at=datetime.utcnow(),
        executed_at=datetime.utcnow(),
    )
    db.add(decision)

    await db.commit()

    from app.routers.stream import publish_event

    await publish_event(
        "agent_action",
        {
            "action": f"Emergency order {order_number}: {quantity}x {product.name}",
            "agent_type": "execution",
            "decision_type": "safety_stock_order",
            "decision_id": decision.id,
            "confidence": 0.85,
        },
    )
    await publish_event(
        "order_update",
        {
            "order_id": order.id,
            "order_number": order_number,
            "status": "pending",
            "action": "created",
        },
    )

    return json.dumps(
        {
            "status": "order_created",
            "order_id": order.id,
            "order_number": order_number,
            "product": product.name,
            "quantity": quantity,
            "supplier": supplier.name,
            "total_cost_usd": round(total_cost, 2),
            "expected_delivery_days": adjusted_lead_time,
            "urgency": urgency,
            "decision_id": decision.id,
        }
    )


async def update_supplier_status(
    db: AsyncSession,
    supplier_id: str,
    is_active: bool,
    reason: str,
) -> str:
    """Activate or deactivate a supplier with an audit trail."""
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        return json.dumps({"error": f"Supplier {supplier_id} not found."})

    old_status = supplier.is_active
    supplier.is_active = is_active

    action = "activated" if is_active else "deactivated"

    # Audit record
    decision = AgentDecision(
        id=str(uuid.uuid4()),
        agent_type="execution",
        decision_type="supplier_status_change",
        decision_summary=f"Supplier {supplier.name} {action}: {reason}",
        reasoning=reason,
        confidence_score=0.90,
        affected_orders="[]",
        parameters=json.dumps(
            {
                "supplier_id": supplier_id,
                "supplier_name": supplier.name,
                "old_status": old_status,
                "new_status": is_active,
            }
        ),
        status="executed",
        decided_at=datetime.utcnow(),
        executed_at=datetime.utcnow(),
    )
    db.add(decision)

    await db.commit()

    from app.routers.stream import publish_event

    await publish_event(
        "agent_action",
        {
            "action": f"Supplier {supplier.name} {action}",
            "agent_type": "execution",
            "decision_type": "supplier_status_change",
            "decision_id": decision.id,
            "confidence": 0.90,
        },
    )
    await publish_event(
        "supply_alert",
        {
            "severity": "high" if not is_active else "info",
            "message": f"Supplier {supplier.name} has been {action}: {reason}",
            "supplier_id": supplier_id,
        },
    )

    return json.dumps(
        {
            "status": action,
            "supplier_id": supplier_id,
            "supplier_name": supplier.name,
            "is_active": is_active,
            "decision_id": decision.id,
            "reason": reason,
        }
    )


async def log_webhook(
    db: AsyncSession,
    event_type: str,
    target: str,
    payload: str,
) -> str:
    """Simulate sending a webhook notification.

    In production this would POST to an external endpoint. For now we log
    the intent as an AgentDecision for full audit traceability.
    """
    decision = AgentDecision(
        id=str(uuid.uuid4()),
        agent_type="execution",
        decision_type="webhook_notification",
        decision_summary=f"Webhook [{event_type}] to {target}",
        reasoning=f"Simulated webhook delivery. Payload: {payload}",
        confidence_score=1.0,
        affected_orders="[]",
        parameters=json.dumps(
            {
                "event_type": event_type,
                "target": target,
                "payload": payload,
                "simulated": True,
            }
        ),
        status="executed",
        decided_at=datetime.utcnow(),
        executed_at=datetime.utcnow(),
    )
    db.add(decision)
    await db.commit()

    from app.routers.stream import publish_event

    await publish_event(
        "agent_action",
        {
            "action": f"Webhook [{event_type}] sent to {target}",
            "agent_type": "execution",
            "decision_type": "webhook_notification",
            "decision_id": decision.id,
            "confidence": 1.0,
        },
    )

    return json.dumps(
        {
            "status": "webhook_logged",
            "decision_id": decision.id,
            "event_type": event_type,
            "target": target,
            "note": "Webhook simulated and logged. In production, this would POST to the target URL.",
        }
    )
