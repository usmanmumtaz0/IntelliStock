"""
Audit and compliance API endpoints.
Phase 9 Week 3: Audit Trail.
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit/resource/{resource_type}/{resource_id}")
def get_resource_audit_history(
    resource_type: str,
    resource_id: str,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get audit history for a specific resource."""
    service = AuditService(db)
    records, total = service.get_logs_by_resource(
        resource_type=resource_type,
        resource_id=resource_id,
        days=days,
        limit=limit,
        offset=offset,
    )
    
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return {
        "data": [
            {
                "id": str(r.id),
                "user_id": r.user_id,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "old_values": r.old_values,
                "new_values": r.new_values,
                "status": r.status,
                "error_message": r.error_message,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ],
        "pagination": {"total": total, "limit": limit, "offset": offset, "pages": pages},
    }


@router.get("/audit/user/{user_id}")
def get_user_audit_history(
    user_id: str,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all actions by a user."""
    service = AuditService(db)
    records, total = service.get_logs_by_user(
        user_id=user_id,
        days=days,
        limit=limit,
        offset=offset,
    )
    
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return {
        "data": [
            {
                "id": str(r.id),
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "status": r.status,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ],
        "pagination": {"total": total, "limit": limit, "offset": offset, "pages": pages},
    }


@router.get("/audit/action/{action}")
def get_action_history(
    action: str,
    days: int = Query(90, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all instances of a specific action."""
    service = AuditService(db)
    records, total = service.get_logs_by_action(
        action=action,
        days=days,
        limit=limit,
        offset=offset,
    )
    
    pages = (total + limit - 1) // limit if total > 0 else 0
    
    return {
        "data": [
            {
                "id": str(r.id),
                "user_id": r.user_id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "status": r.status,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ],
        "pagination": {"total": total, "limit": limit, "offset": offset, "pages": pages},
    }


@router.get("/audit/failures")
def get_failed_actions(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all failed actions (for error tracking and debugging)."""
    service = AuditService(db)
    records = service.get_failed_actions(days=days, limit=limit)
    
    return {
        "count": len(records),
        "data": [
            {
                "id": str(r.id),
                "user_id": r.user_id,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "error_message": r.error_message,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in records
        ],
    }
