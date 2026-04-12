"""Tests for the alerting rules engine."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlertRule
from app.services import alert_rule_service


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rule(db_session: AsyncSession):
    """create_rule persists a rule and returns it."""
    rule = await alert_rule_service.create_rule(
        db_session,
        name="Low reliability alert",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.7,
        severity="high",
        description="Alert when supplier reliability drops below 0.7",
    )

    assert rule.id is not None
    assert rule.name == "Low reliability alert"
    assert rule.metric == "supplier_reliability"
    assert rule.operator == "lt"
    assert float(rule.threshold) == 0.7
    assert rule.is_enabled is True
    assert rule.trigger_count == 0


@pytest.mark.asyncio
async def test_list_rules(db_session: AsyncSession):
    """list_rules returns all rules."""
    await alert_rule_service.create_rule(
        db_session,
        name="Rule A",
        metric="risk_event_count",
        operator="gt",
        threshold=5,
    )
    await alert_rule_service.create_rule(
        db_session,
        name="Rule B",
        metric="order_delay_days",
        operator="gt",
        threshold=7,
    )

    rules = await alert_rule_service.list_rules(db_session)
    assert len(rules) >= 2


@pytest.mark.asyncio
async def test_list_rules_enabled_only(db_session: AsyncSession):
    """list_rules with enabled_only filters disabled rules."""
    rule = await alert_rule_service.create_rule(
        db_session,
        name="Disabled rule",
        metric="risk_event_count",
        operator="gt",
        threshold=10,
    )
    await alert_rule_service.toggle_rule(db_session, rule.id)

    enabled = await alert_rule_service.list_rules(db_session, enabled_only=True)
    assert all(r.is_enabled for r in enabled)


@pytest.mark.asyncio
async def test_get_rule(db_session: AsyncSession):
    """get_rule returns a specific rule by ID."""
    rule = await alert_rule_service.create_rule(
        db_session,
        name="Get test",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.5,
    )

    fetched = await alert_rule_service.get_rule(db_session, rule.id)
    assert fetched is not None
    assert fetched.id == rule.id


@pytest.mark.asyncio
async def test_get_rule_not_found(db_session: AsyncSession):
    """get_rule returns None for nonexistent ID."""
    result = await alert_rule_service.get_rule(db_session, str(uuid.uuid4()))
    assert result is None


@pytest.mark.asyncio
async def test_update_rule(db_session: AsyncSession):
    """update_rule modifies the rule's fields."""
    rule = await alert_rule_service.create_rule(
        db_session,
        name="Original name",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.7,
    )

    updated = await alert_rule_service.update_rule(
        db_session,
        rule.id,
        name="Updated name",
        threshold=0.6,
    )
    assert updated is not None
    assert updated.name == "Updated name"
    assert float(updated.threshold) == 0.6


@pytest.mark.asyncio
async def test_delete_rule(db_session: AsyncSession):
    """delete_rule removes the rule."""
    rule = await alert_rule_service.create_rule(
        db_session,
        name="To delete",
        metric="risk_event_count",
        operator="gt",
        threshold=5,
    )

    deleted = await alert_rule_service.delete_rule(db_session, rule.id)
    assert deleted is True

    fetched = await alert_rule_service.get_rule(db_session, rule.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_toggle_rule(db_session: AsyncSession):
    """toggle_rule flips is_enabled."""
    rule = await alert_rule_service.create_rule(
        db_session,
        name="Toggle test",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.5,
    )
    assert rule.is_enabled is True

    toggled = await alert_rule_service.toggle_rule(db_session, rule.id)
    assert toggled is not None
    assert toggled.is_enabled is False

    toggled2 = await alert_rule_service.toggle_rule(db_session, rule.id)
    assert toggled2 is not None
    assert toggled2.is_enabled is True


# ---------------------------------------------------------------------------
# Evaluation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_supplier_reliability_rule(seeded_db: AsyncSession):
    """Rule fires when supplier reliability is below threshold."""
    rule = await alert_rule_service.create_rule(
        seeded_db,
        name="Low reliability",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.99,  # Most suppliers will be below this
        severity="high",
        trigger_agent_analysis=False,
    )

    violations = await alert_rule_service.evaluate_rule(seeded_db, rule)
    assert len(violations) > 0
    for v in violations:
        assert v["metric_value"] < 0.99


@pytest.mark.asyncio
async def test_evaluate_rule_no_violations(seeded_db: AsyncSession):
    """Rule returns empty when no violations."""
    rule = await alert_rule_service.create_rule(
        seeded_db,
        name="Impossible threshold",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.0,  # No supplier has negative reliability
        trigger_agent_analysis=False,
    )

    violations = await alert_rule_service.evaluate_rule(seeded_db, rule)
    assert len(violations) == 0


@pytest.mark.asyncio
async def test_evaluate_risk_event_count(seeded_db: AsyncSession):
    """risk_event_count rule fires when count exceeds threshold."""
    rule = await alert_rule_service.create_rule(
        seeded_db,
        name="Many events",
        metric="risk_event_count",
        operator="gt",
        threshold=0,  # We have seed events
        trigger_agent_analysis=False,
    )

    violations = await alert_rule_service.evaluate_rule(seeded_db, rule)
    assert len(violations) > 0


@pytest.mark.asyncio
async def test_evaluate_composite_risk_score(seeded_db: AsyncSession):
    """composite_risk_score rule fires for high-risk suppliers."""
    rule = await alert_rule_service.create_rule(
        seeded_db,
        name="High composite risk",
        metric="composite_risk_score",
        operator="gt",
        threshold=0.0,  # Should catch at least some
        trigger_agent_analysis=False,
    )

    violations = await alert_rule_service.evaluate_rule(seeded_db, rule)
    assert len(violations) > 0


@pytest.mark.asyncio
async def test_evaluate_all_rules_respects_cooldown(seeded_db: AsyncSession):
    """evaluate_all_rules skips rules still in cooldown."""
    from datetime import datetime

    rule = await alert_rule_service.create_rule(
        seeded_db,
        name="Cooldown test",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.99,
        trigger_agent_analysis=False,
        cooldown_minutes=9999,
    )
    # Manually set last_triggered_at to now
    rule.last_triggered_at = datetime.utcnow()
    await seeded_db.flush()

    summary = await alert_rule_service.evaluate_all_rules(seeded_db)
    # Rule should be skipped due to cooldown
    triggered_ids = [t["rule_id"] for t in summary["triggered_rules"]]
    assert rule.id not in triggered_ids


@pytest.mark.asyncio
async def test_evaluate_all_rules_creates_alerts(seeded_db: AsyncSession):
    """evaluate_all_rules creates risk alerts for triggered rules."""
    await alert_rule_service.create_rule(
        seeded_db,
        name="Fires easily",
        metric="supplier_reliability",
        operator="lt",
        threshold=0.99,
        severity="medium",
        trigger_agent_analysis=False,
    )

    summary = await alert_rule_service.evaluate_all_rules(seeded_db)
    assert summary["rules_triggered"] >= 1
    assert summary["alerts_created"] >= 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_rules_endpoint(seeded_client):
    """GET /api/v1/alert-rules returns the list."""
    resp = await seeded_client.get("/api/v1/alert-rules/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "id" in first
    assert "name" in first
    assert "metric" in first
    assert "threshold" in first


@pytest.mark.asyncio
async def test_create_rule_endpoint(seeded_client):
    """POST /api/v1/alert-rules creates a new rule."""
    resp = await seeded_client.post(
        "/api/v1/alert-rules/",
        json={
            "name": "API test rule",
            "metric": "supplier_reliability",
            "operator": "lt",
            "threshold": 0.5,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "API test rule"
    assert data["is_enabled"] is True


@pytest.mark.asyncio
async def test_get_rule_endpoint(seeded_client):
    """GET /api/v1/alert-rules/:id returns full detail."""
    list_resp = await seeded_client.get("/api/v1/alert-rules/", params={"limit": 1})
    rules = list_resp.json()
    assert len(rules) > 0

    rule_id = rules[0]["id"]
    resp = await seeded_client.get(f"/api/v1/alert-rules/{rule_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == rule_id
    assert "description" in data
    assert "cooldown_minutes" in data


@pytest.mark.asyncio
async def test_toggle_rule_endpoint(seeded_client):
    """POST /api/v1/alert-rules/:id/toggle flips enabled state."""
    list_resp = await seeded_client.get("/api/v1/alert-rules/", params={"limit": 1})
    rule_id = list_resp.json()[0]["id"]
    original_enabled = list_resp.json()[0]["is_enabled"]

    resp = await seeded_client.post(f"/api/v1/alert-rules/{rule_id}/toggle")
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] != original_enabled


@pytest.mark.asyncio
async def test_delete_rule_endpoint(seeded_client):
    """DELETE /api/v1/alert-rules/:id removes the rule."""
    create_resp = await seeded_client.post(
        "/api/v1/alert-rules/",
        json={
            "name": "To delete via API",
            "metric": "risk_event_count",
            "operator": "gt",
            "threshold": 100,
        },
    )
    rule_id = create_resp.json()["id"]

    resp = await seeded_client.delete(f"/api/v1/alert-rules/{rule_id}")
    assert resp.status_code == 204

    get_resp = await seeded_client.get(f"/api/v1/alert-rules/{rule_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_endpoint(seeded_client):
    """POST /api/v1/alert-rules/evaluate triggers evaluation."""
    resp = await seeded_client.post("/api/v1/alert-rules/evaluate")
    assert resp.status_code == 200
    data = resp.json()
    assert "rules_evaluated" in data
    assert "rules_triggered" in data
    assert "alerts_created" in data


@pytest.mark.asyncio
async def test_get_rule_not_found_endpoint(seeded_client):
    """GET /api/v1/alert-rules/:id returns 404 for missing ID."""
    resp = await seeded_client.get(f"/api/v1/alert-rules/{uuid.uuid4()}")
    assert resp.status_code == 404
