"""
Health monitoring API endpoints.
Phase 9 Week 3: Health Monitoring.
"""
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.health_monitor import HealthMonitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health/system")
def get_system_health(db: Session = Depends(get_db)):
    """Get overall system health status."""
    monitor = HealthMonitor(db)
    return monitor.get_system_health()


@router.get("/health/database")
def check_database_health(db: Session = Depends(get_db)):
    """Check database component health."""
    monitor = HealthMonitor(db)
    return monitor.check_database_health()


@router.get("/health/redis")
def check_redis_health(db: Session = Depends(get_db)):
    """Check Redis component health."""
    monitor = HealthMonitor(db)
    return monitor.check_redis_health()


@router.get("/health/performance/{component}/{operation}")
def get_operation_performance(
    component: str,
    operation: str,
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get performance statistics for an operation."""
    monitor = HealthMonitor(db)
    stats = monitor.get_performance_stats(
        component=component,
        operation=operation,
        days=days,
    )
    return stats


@router.get("/health/performance/issues")
def get_performance_issues(
    threshold_ms: float = Query(1000, ge=100, le=10000),
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get slow operations exceeding performance threshold."""
    monitor = HealthMonitor(db)
    issues = monitor.get_recent_performance_issues(
        threshold_ms=threshold_ms,
        days=days,
    )
    
    return {
        "threshold_ms": threshold_ms,
        "count": len(issues),
        "data": [
            {
                "component": issue.component,
                "operation": issue.operation,
                "duration_ms": issue.duration_ms,
                "recorded_at": issue.recorded_at.isoformat(),
            }
            for issue in issues
        ],
    }


@router.get("/health/failures")
def get_failed_operations(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Get failed operations (errors)."""
    monitor = HealthMonitor(db)
    failures = monitor.get_failed_operations(days=days)
    
    return {
        "count": len(failures),
        "data": [
            {
                "component": failure.component,
                "operation": failure.operation,
                "duration_ms": failure.duration_ms,
                "error_message": failure.error_message,
                "recorded_at": failure.recorded_at.isoformat(),
            }
            for failure in failures
        ],
    }
