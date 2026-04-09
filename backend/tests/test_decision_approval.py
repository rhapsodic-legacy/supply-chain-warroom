"""Tests for the human-in-the-loop decision approval flow."""

from __future__ import annotations

import pytest


class TestDecisionApprovalAPI:
    """Test the PATCH /api/v1/agents/decisions/{id} endpoint."""

    async def _get_proposed_decision(self, client):
        """Find or verify a proposed decision exists in seed data."""
        resp = await client.get("/api/v1/agents/decisions", params={"status": "proposed"})
        assert resp.status_code == 200
        decisions = resp.json()
        if decisions:
            return decisions[0]
        return None

    @pytest.mark.asyncio
    async def test_approve_proposed_decision(self, seeded_client):
        decision = await self._get_proposed_decision(seeded_client)
        if not decision:
            pytest.skip("No proposed decisions in seed data")

        resp = await seeded_client.patch(
            f"/api/v1/agents/decisions/{decision['id']}",
            json={"action": "approve", "notes": "Looks good, proceed."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["outcome"] == "approved"
        assert data["outcome_notes"] == "Looks good, proceed."
        assert data["executed_at"] is not None

    @pytest.mark.asyncio
    async def test_reject_proposed_decision(self, seeded_client):
        # Find another proposed decision
        resp = await seeded_client.get(
            "/api/v1/agents/decisions", params={"status": "proposed"}
        )
        decisions = resp.json()
        if not decisions:
            pytest.skip("No proposed decisions in seed data")

        decision = decisions[0]
        resp = await seeded_client.patch(
            f"/api/v1/agents/decisions/{decision['id']}",
            json={"action": "reject", "notes": "Too risky."},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["outcome"] == "rejected"

    @pytest.mark.asyncio
    async def test_cannot_approve_executed_decision(self, seeded_client):
        resp = await seeded_client.get(
            "/api/v1/agents/decisions", params={"status": "executed"}
        )
        decisions = resp.json()
        if not decisions:
            pytest.skip("No executed decisions in seed data")

        resp = await seeded_client.patch(
            f"/api/v1/agents/decisions/{decisions[0]['id']}",
            json={"action": "approve"},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_404_for_missing_decision(self, seeded_client):
        resp = await seeded_client.patch(
            "/api/v1/agents/decisions/nonexistent-id",
            json={"action": "approve"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_action_rejected(self, seeded_client):
        resp = await seeded_client.patch(
            "/api/v1/agents/decisions/any-id",
            json={"action": "invalid"},
        )
        assert resp.status_code == 422
