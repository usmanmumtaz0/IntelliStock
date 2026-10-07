"""
Agent endpoints — Track and manage AI agent executions.
Used for FYP evaluation evidence and debugging.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.database import get_db
from app.models.agent_run import AgentRun, AgentRunStatus

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


class AgentRunResponse(BaseModel):
    id: str
    agent_type: str
    status: str
    trigger_event: Optional[str]
    output_action: Optional[str]
    confidence_score: Optional[float]
    execution_time_ms: Optional[int]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/runs", response_model=List[AgentRunResponse])
def list_agent_runs(
    agent_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    hours: int = Query(24, ge=1, le=720),
    db: Session = Depends(get_db),
):
    """
    List agent run history for FYP evaluation.
    
    Args:
        agent_type: Filter by agent type (supervisor, insight, anomaly, notification)
        status: Filter by status (pending, running, completed, failed)
        limit: Max runs to return
        hours: Look back this many hours
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(AgentRun).filter(AgentRun.created_at >= since)
    
    if agent_type:
        query = query.filter(AgentRun.agent_type == agent_type)
    if status:
        query = query.filter(AgentRun.status == status)
    
    runs = query.order_by(AgentRun.created_at.desc()).limit(limit).all()
    return runs


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
def get_agent_run(run_id: str, db: Session = Depends(get_db)):
    """Get details of a specific agent run."""
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    return run


@router.get("/runs/{run_id}/trace")
def get_agent_run_trace(run_id: str, db: Session = Depends(get_db)):
    """Get full execution trace of an agent run (for debugging)."""
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found")
    
    return {
        "run_id": run.id,
        "agent": run.agent_type,
        "status": run.status,
        "trigger_event": run.trigger_event,
        "trigger_data": run.trigger_data,
        "input": run.input_prompt,
        "reasoning": run.reasoning,
        "output_action": run.output_action,
        "output_data": run.output_data,
        "confidence": run.confidence_score,
        "llm_model": run.llm_model,
        "llm_provider": run.llm_provider,
        "tokens_used": run.tokens_used,
        "execution_time_ms": run.execution_time_ms,
        "error": run.error_message,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
    }


@router.get("/stats")
def get_agent_stats(hours: int = Query(24, ge=1, le=720), db: Session = Depends(get_db)):
    """Get statistics about agent performance."""
    since = datetime.utcnow() - timedelta(hours=hours)
    
    total_runs = db.query(AgentRun).filter(AgentRun.created_at >= since).count()
    completed_runs = db.query(AgentRun).filter(
        AgentRun.created_at >= since,
        AgentRun.status == AgentRunStatus.COMPLETED
    ).count()
    failed_runs = db.query(AgentRun).filter(
        AgentRun.created_at >= since,
        AgentRun.status == AgentRunStatus.FAILED
    ).count()
    
    # Stats by agent type
    by_type = {}
    for agent_type in ["supervisor", "insight", "anomaly", "notification"]:
        count = db.query(AgentRun).filter(
            AgentRun.created_at >= since,
            AgentRun.agent_type == agent_type
        ).count()
        by_type[agent_type] = count
    
    # Average confidence (completed runs)
    completed = db.query(AgentRun).filter(
        AgentRun.created_at >= since,
        AgentRun.status == AgentRunStatus.COMPLETED,
        AgentRun.confidence_score.isnot(None)
    ).all()
    avg_confidence = sum(r.confidence_score for r in completed) / len(completed) if completed else 0.0
    
    return {
        "period_hours": hours,
        "total_runs": total_runs,
        "completed": completed_runs,
        "failed": failed_runs,
        "success_rate": completed_runs / max(total_runs, 1),
        "by_agent_type": by_type,
        "average_confidence": avg_confidence,
    }
