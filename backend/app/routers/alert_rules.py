from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import (
    AlertRuleBrief,
    AlertRuleCreate,
    AlertRuleEvalSummary,
    AlertRuleResponse,
    AlertRuleUpdate,
)
from app.services import alert_rule_service

router = APIRouter(prefix="/api/v1/alert-rules", tags=["alert-rules"])


@router.get("", response_model=list[AlertRuleBrief])
async def list_rules(
    enabled_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    return await alert_rule_service.list_rules(db, enabled_only=enabled_only, limit=limit)


@router.post("", response_model=AlertRuleResponse, status_code=201)
async def create_rule(body: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    return await alert_rule_service.create_rule(db, **body.model_dump())


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    rule = await alert_rule_service.get_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.patch("/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(rule_id: str, body: AlertRuleUpdate, db: AsyncSession = Depends(get_db)):
    updates = body.model_dump(exclude_unset=True)
    rule = await alert_rule_service.update_rule(db, rule_id, **updates)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await alert_rule_service.delete_rule(db, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert rule not found")


@router.post("/{rule_id}/toggle", response_model=AlertRuleResponse)
async def toggle_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    """Enable or disable an alert rule."""
    rule = await alert_rule_service.toggle_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    return rule


@router.post("/evaluate", response_model=AlertRuleEvalSummary)
async def evaluate_rules(db: AsyncSession = Depends(get_db)):
    """Manually trigger evaluation of all enabled alert rules."""
    return await alert_rule_service.evaluate_all_rules(db)
