"""FastAPI <-> Agent bridge.

Provides a clean entry point for the API layer to invoke the agent system
without importing internal agent details. The router calls
``chat_with_orchestrator`` and gets back a Pydantic ``ChatResponse``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.orchestrator import run_orchestrator
from app.schemas import ChatResponse


async def chat_with_orchestrator(db: AsyncSession, message: str) -> ChatResponse:
    """Entry point called by the /api/v1/agents/chat endpoint.

    Delegates to the orchestrator agent and wraps the result in the
    API response schema.
    """
    result = await run_orchestrator(db, message)
    return ChatResponse(
        response=result["response"],
        agent_actions=result.get("actions", []),
        timestamp=datetime.utcnow(),
    )
