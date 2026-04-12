from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    AgentDecisionBrief,
    AgentDecisionResponse,
    AgentHandoffResponse,
    AgentHandoffSessionResponse,
    AgentMemoryBrief,
    AgentMemoryResponse,
    AgentMemoryStats,
    ChatRequest,
    ChatResponse,
    DecisionStatusUpdate,
)
from app.services import agent_service
from app.services import handoff_service
from app.services import memory_service

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/decisions", response_model=list[AgentDecisionBrief])
async def list_decisions(
    agent_type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await agent_service.list_decisions(db, agent_type=agent_type, status=status, limit=limit)


@router.get("/decisions/{decision_id}", response_model=AgentDecisionResponse)
async def get_decision(decision_id: str, db: AsyncSession = Depends(get_db)):
    decision = await agent_service.get_decision(db, decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Agent decision not found")
    return decision


@router.patch("/decisions/{decision_id}", response_model=AgentDecisionResponse)
async def update_decision_status(
    decision_id: str,
    body: DecisionStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a proposed agent decision."""
    try:
        result = await agent_service.update_decision_status(
            db, decision_id, action=body.action, notes=body.notes
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Agent decision not found")
    return result


@router.get("/handoffs", response_model=list[AgentHandoffResponse])
async def list_handoffs(
    session_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await handoff_service.list_handoffs(db, session_id=session_id, limit=limit)


@router.get("/handoffs/sessions", response_model=list[AgentHandoffSessionResponse])
async def list_handoff_sessions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await handoff_service.list_sessions(db, limit=limit)


# ---------------------------------------------------------------------------
# Memory endpoints
# ---------------------------------------------------------------------------


@router.get("/memories", response_model=list[AgentMemoryBrief])
async def list_memories(
    agent_type: str | None = Query(None),
    category: str | None = Query(None),
    outcome: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await memory_service.list_memories(
        db, agent_type=agent_type, category=category, outcome=outcome, limit=limit
    )


@router.get("/memories/stats", response_model=AgentMemoryStats)
async def get_memory_stats(db: AsyncSession = Depends(get_db)):
    return await memory_service.get_memory_stats(db)


@router.get("/memories/{memory_id}", response_model=AgentMemoryResponse)
async def get_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    memory = await memory_service.get_memory(db, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Agent memory not found")
    return memory


# ---------------------------------------------------------------------------
# Chat endpoint
# ---------------------------------------------------------------------------


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        from app.agents.orchestrator import handle_chat

        result = await handle_chat(request.message, db)
        return result
    except ImportError:
        return ChatResponse(
            response="Agent orchestrator is not yet configured. Please set up the agents module.",
            agent_actions=[],
            timestamp=datetime.utcnow(),
        )
