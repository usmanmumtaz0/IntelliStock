"""
Health monitoring service for system performance and component status.
Phase 9 Week 3: Health Monitoring.
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.system_health import SystemHealthMetric, PerformanceLog, ComponentStatus, HealthCheckType
from app.core.health import check_database, check_redis

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitors system health and records performance metrics."""

    def __init__(self, db: Session):
        self.db = db

    def check_database_health(self) -> Dict:
        """Check database health."""
        start = time.time()
        is_healthy = check_database()
        duration = (time.time() - start) * 1000
        
        status = ComponentStatus.HEALTHY if is_healthy else ComponentStatus.UNHEALTHY
        
        metric = SystemHealthMetric(
            component=HealthCheckType.DATABASE,
            status=status,
            response_time_ms=duration,
            error_rate=0.0 if is_healthy else 1.0,
            message="Database is responsive" if is_healthy else "Database connection failed",
            check_duration_ms=int(duration),
        )
        self.db.add(metric)
        self.db.commit()
        
        return {
            "component": HealthCheckType.DATABASE.value,
            "status": status.value,
            "response_time_ms": duration,
            "is_healthy": is_healthy,
        }

    def check_redis_health(self) -> Dict:
        """Check Redis health."""
        start = time.time()
        is_healthy = check_redis()
        duration = (time.time() - start) * 1000
        
        status = ComponentStatus.HEALTHY if is_healthy else ComponentStatus.UNHEALTHY
        
        metric = SystemHealthMetric(
            component=HealthCheckType.REDIS,
            status=status,
            response_time_ms=duration,
            error_rate=0.0 if is_healthy else 1.0,
            message="Redis is responsive" if is_healthy else "Redis connection failed",
            check_duration_ms=int(duration),
        )
        self.db.add(metric)
        self.db.commit()
        
        return {
            "component": HealthCheckType.REDIS.value,
            "status": status.value,
            "response_time_ms": duration,
            "is_healthy": is_healthy,
        }

    def record_performance(
        self,
        component: str,
        operation: str,
        duration_ms: float,
        success: bool = True,
        error_message: str = None,
        resource_id: str = None,
        batch_size: int = None,
    ) -> PerformanceLog:
        """Record performance metric for operation."""
        log = PerformanceLog(
            component=component,
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            resource_id=resource_id,
            batch_size=batch_size,
        )
        self.db.add(log)
        self.db.commit()
        return log

    def get_performance_stats(
        self,
        component: str,
        operation: str,
        days: int = 7,
    ) -> Dict:
        """Get performance statistics for an operation."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        logs = self.db.query(PerformanceLog).filter(
            PerformanceLog.component == component,
            PerformanceLog.operation == operation,
            PerformanceLog.recorded_at >= cutoff,
        ).all()
        
        if not logs:
            return {
                "component": component,
                "operation": operation,
                "count": 0,
                "avg_duration_ms": 0,
                "min_duration_ms": 0,
                "max_duration_ms": 0,
                "success_rate": 1.0,
            }
        
        durations = [log.duration_ms for log in logs]
        successes = sum(1 for log in logs if log.success)
        
        return {
            "component": component,
            "operation": operation,
            "count": len(logs),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "success_rate": successes / len(logs),
            "slowest": max(durations),
        }

    def get_system_health(self) -> Dict:
        """Get overall system health status."""
        # Get latest health metrics
        metrics = self.db.query(SystemHealthMetric).order_by(
            desc(SystemHealthMetric.checked_at)
        ).limit(len(HealthCheckType)).all()
        
        if not metrics:
            return {"status": "UNKNOWN", "components": []}
        
        components = []
        overall_healthy = True
        
        for metric in metrics:
            components.append({
                "component": metric.component.value,
                "status": metric.status.value,
                "response_time_ms": metric.response_time_ms,
                "error_rate": metric.error_rate,
            })
            if metric.status != ComponentStatus.HEALTHY:
                overall_healthy = False
        
        overall_status = "HEALTHY" if overall_healthy else "DEGRADED"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components,
        }

    def get_recent_performance_issues(
        self,
        threshold_ms: float = 1000,
        days: int = 7,
    ) -> List[PerformanceLog]:
        """Get slow operations exceeding threshold."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(PerformanceLog).filter(
            PerformanceLog.duration_ms > threshold_ms,
            PerformanceLog.recorded_at >= cutoff,
        ).order_by(desc(PerformanceLog.duration_ms)).limit(100).all()

    def get_failed_operations(
        self,
        days: int = 7,
    ) -> List[PerformanceLog]:
        """Get all failed operations."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(PerformanceLog).filter(
            PerformanceLog.success == False,
            PerformanceLog.recorded_at >= cutoff,
        ).order_by(desc(PerformanceLog.recorded_at)).limit(100).all()

    def cleanup_old_metrics(self, retention_days: int = 90):
        """Delete metrics older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted_metrics = (
            self.db.query(SystemHealthMetric)
            .filter(SystemHealthMetric.checked_at < cutoff)
            .delete(synchronize_session=False)
        )
        
        deleted_logs = (
            self.db.query(PerformanceLog)
            .filter(PerformanceLog.recorded_at < cutoff)
            .delete(synchronize_session=False)
        )
        
        self.db.commit()
        logger.info(f"Deleted {deleted_metrics} metrics and {deleted_logs} logs")
        return deleted_metrics + deleted_logs
