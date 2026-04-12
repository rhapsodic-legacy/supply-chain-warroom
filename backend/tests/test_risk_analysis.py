"""Tests for the automated risk analysis pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import RiskEvent, Supplier
from app.services.risk_analysis import (
    REGIONAL_ESCALATION_THRESHOLD,
    _check_regional_escalation,
    _get_new_events,
    _score_suppliers,
    run_triage,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_supplier(region: str = "East Asia", reliability: float = 0.85, **kw) -> Supplier:
    return Supplier(
        id=kw.get("id", str(uuid.uuid4())),
        name=kw.get("name", f"Supplier-{uuid.uuid4().hex[:6]}"),
        country=kw.get("country", "China"),
        region=region,
        city=kw.get("city", "Shanghai"),
        reliability_score=reliability,
        base_lead_time_days=kw.get("lead_time", 14),
        lead_time_variance=2,
        cost_multiplier=1.0,
        capacity_units=10_000,
        is_active=kw.get("is_active", True),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _make_risk_event(
    severity: str = "high",
    region: str = "East Asia",
    event_type: str = "geopolitical",
    **kw,
) -> RiskEvent:
    score_map = {"low": 0.3, "medium": 0.5, "high": 0.7, "critical": 0.9}
    return RiskEvent(
        id=kw.get("id", str(uuid.uuid4())),
        event_type=event_type,
        title=kw.get("title", f"Test risk event — {uuid.uuid4().hex[:6]}"),
        description=kw.get("description", "Test event for risk analysis"),
        severity=severity,
        severity_score=score_map.get(severity, 0.5),
        affected_region=region,
        started_at=datetime.utcnow(),
        is_active=kw.get("is_active", True),
        created_at=kw.get("created_at", datetime.utcnow()),
    )


# ---------------------------------------------------------------------------
# Supplier scoring
# ---------------------------------------------------------------------------


class TestSupplierScoring:
    @pytest.mark.asyncio
    async def test_scores_reflect_regional_risk(self, db_session):
        """Suppliers in regions with more active risk events score higher."""
        s1 = _make_supplier(region="East Asia", reliability=0.90, name="EA Supplier")
        s2 = _make_supplier(region="Europe", reliability=0.90, name="EU Supplier")
        db_session.add_all([s1, s2])

        # Add 4 active risk events in East Asia, 0 in Europe
        for _ in range(4):
            db_session.add(_make_risk_event(severity="high", region="East Asia"))
        await db_session.flush()

        scores = await _score_suppliers(db_session)
        by_name = {s["supplier_name"]: s for s in scores}

        assert (
            by_name["EA Supplier"]["composite_risk_score"]
            > by_name["EU Supplier"]["composite_risk_score"]
        )

    @pytest.mark.asyncio
    async def test_low_reliability_increases_score(self, db_session):
        """A supplier with low reliability should score higher risk."""
        s_good = _make_supplier(reliability=0.95, name="Reliable")
        s_bad = _make_supplier(reliability=0.50, name="Unreliable")
        db_session.add_all([s_good, s_bad])
        await db_session.flush()

        scores = await _score_suppliers(db_session)
        by_name = {s["supplier_name"]: s for s in scores}

        assert (
            by_name["Unreliable"]["composite_risk_score"]
            > by_name["Reliable"]["composite_risk_score"]
        )


# ---------------------------------------------------------------------------
# Regional escalation
# ---------------------------------------------------------------------------


class TestRegionalEscalation:
    @pytest.mark.asyncio
    async def test_detects_escalation(self, db_session):
        """Regions with >= THRESHOLD active high/critical events are flagged."""
        for _ in range(REGIONAL_ESCALATION_THRESHOLD):
            db_session.add(_make_risk_event(severity="critical", region="South Asia"))
        await db_session.flush()

        escalations = await _check_regional_escalation(db_session)
        regions = [e["region"] for e in escalations]
        assert "South Asia" in regions

    @pytest.mark.asyncio
    async def test_no_escalation_below_threshold(self, db_session):
        """Regions below the threshold should not appear."""
        db_session.add(_make_risk_event(severity="high", region="North America"))
        await db_session.flush()

        escalations = await _check_regional_escalation(db_session)
        regions = [e["region"] for e in escalations]
        assert "North America" not in regions

    @pytest.mark.asyncio
    async def test_low_severity_not_counted(self, db_session):
        """Low/medium events should not trigger regional escalation."""
        for _ in range(5):
            db_session.add(_make_risk_event(severity="low", region="Europe"))
        await db_session.flush()

        escalations = await _check_regional_escalation(db_session)
        regions = [e["region"] for e in escalations]
        assert "Europe" not in regions


# ---------------------------------------------------------------------------
# New event detection
# ---------------------------------------------------------------------------


class TestNewEventDetection:
    @pytest.mark.asyncio
    async def test_finds_recent_events(self, db_session):
        """Events created in the last 35 minutes should be returned."""
        recent = _make_risk_event(title="Recent event", created_at=datetime.utcnow())
        db_session.add(recent)
        await db_session.flush()

        new = await _get_new_events(db_session)
        titles = [e.title for e in new]
        assert "Recent event" in titles

    @pytest.mark.asyncio
    async def test_excludes_old_events(self, db_session):
        """Events older than the window should not appear."""
        old = _make_risk_event(
            title="Old event",
            created_at=datetime.utcnow() - timedelta(hours=2),
        )
        db_session.add(old)
        await db_session.flush()

        new = await _get_new_events(db_session)
        titles = [e.title for e in new]
        assert "Old event" not in titles


# ---------------------------------------------------------------------------
# Full triage
# ---------------------------------------------------------------------------


class TestRunTriage:
    @pytest.mark.asyncio
    async def test_triage_skips_on_zero_events(self, db_session):
        """No new events → triage returns early with no actions."""
        result = await run_triage(db_session, new_event_count=0)
        assert result["new_events_ingested"] == 0
        assert result["alerts_created"] == 0

    @pytest.mark.asyncio
    async def test_triage_creates_regional_escalation_alert(self, db_session):
        """When a region has enough high/critical events, an alert is created."""
        for _ in range(REGIONAL_ESCALATION_THRESHOLD + 1):
            db_session.add(_make_risk_event(severity="critical", region="Middle East"))
        db_session.add(_make_supplier(region="Middle East", name="ME Supplier"))
        await db_session.flush()

        result = await run_triage(db_session, new_event_count=3)

        assert result["alerts_created"] >= 1
        assert any(e["region"] == "Middle East" for e in result["regional_escalations"])

        # Verify the alert was persisted
        alert_result = await db_session.execute(
            select(RiskEvent).where(
                RiskEvent.event_type == "agent_alert",
                RiskEvent.title.contains("Middle East"),
            )
        )
        alert = alert_result.scalar_one_or_none()
        assert alert is not None
        assert alert.severity in ("high", "critical")

    @pytest.mark.asyncio
    async def test_triage_does_not_duplicate_alerts(self, db_session):
        """Running triage twice should not create duplicate regional alerts."""
        for _ in range(REGIONAL_ESCALATION_THRESHOLD + 1):
            db_session.add(_make_risk_event(severity="critical", region="Central Asia"))
        db_session.add(_make_supplier(region="Central Asia", name="CA Supplier"))
        await db_session.flush()

        await run_triage(db_session, new_event_count=3)
        await db_session.commit()

        result2 = await run_triage(db_session, new_event_count=1)

        # Second run should find the existing alert and skip creation
        assert result2["alerts_created"] == 0
