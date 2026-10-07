"""
System health and performance monitoring model.
Phase 9 Week 3: Health Monitoring.
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Enum as SQLEnum
from app.models.base import BaseModel
from enum import Enum as PyEnum
from datetime import datetime


class ComponentStatus(str, PyEnum):
    """Health status of system components."""
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"


class HealthCheckType(str, PyEnum):
    """Types of health checks."""
    DATABASE = "DATABASE"
    REDIS = "REDIS"
    CV_DETECTION = "CV_DETECTION"
    RECONCILIATION = "RECONCILIATION"
    ALERT_ENGINE = "ALERT_ENGINE"
    API = "API"
    STORAGE = "STORAGE"
    NETWORK = "NETWORK"
    SYSTEM_RESOURCE = "SYSTEM_RESOURCE"


class SystemHealthMetric(BaseModel):
    """Health metric snapshot for monitoring."""

    __tablename__ = "system_health_metrics"

    # Component being monitored
    component = Column(SQLEnum(HealthCheckType), nullable=False, index=True)
    status = Column(SQLEnum(ComponentStatus), nullable=False, index=True)

    # Performance metrics
    response_time_ms = Column(Float, nullable=True)  # Avg response time
    error_rate = Column(Float, nullable=True)  # 0.0-1.0, errors/total
    throughput = Column(Float, nullable=True)  # Requests/sec or items/sec
    
    # Resource usage
    cpu_percent = Column(Float, nullable=True)  # 0-100
    memory_percent = Column(Float, nullable=True)  # 0-100
    disk_percent = Column(Float, nullable=True)  # 0-100
    connection_count = Column(Integer, nullable=True)  # Active connections

    # Database metrics (if applicable)
    query_count = Column(Integer, nullable=True)  # Queries since last check
    slow_query_count = Column(Integer, nullable=True)  # Queries >threshold
    connection_pool_active = Column(Integer, nullable=True)
    connection_pool_idle = Column(Integer, nullable=True)

    # Detection metrics (if CV detection component)
    detections_processed = Column(Integer, nullable=True)
    avg_confidence = Column(Float, nullable=True)
    failed_detections = Column(Integer, nullable=True)

    # Alert metrics (if alert engine)
    alerts_generated = Column(Integer, nullable=True)
    alerts_processed = Column(Integer, nullable=True)
    avg_alert_latency_ms = Column(Float, nullable=True)

    # Details
    message = Column(String(500), nullable=True)  # Status message
    last_error = Column(String(500), nullable=True)
    
    # Monitoring
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    check_duration_ms = Column(Integer, nullable=True)  # How long check took
    last_failure_at = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    
    # Thresholds for alerting
    alert_threshold = Column(Float, nullable=True)  # Trigger alert if > this
    critical_threshold = Column(Float, nullable=True)  # Critical if > this

    def __repr__(self):
        return (
            f"<SystemHealth {self.component.value} {self.status.value} "
            f"response={self.response_time_ms}ms error={self.error_rate}>"
        )


class PerformanceLog(BaseModel):
    """Performance metrics log for trending and analysis."""

    __tablename__ = "performance_logs"

    # Component
    component = Column(String(100), nullable=False, index=True)
    operation = Column(String(100), nullable=False)  # e.g., "reconcile", "query_history"

    # Execution metrics
    duration_ms = Column(Float, nullable=False)
    cpu_time_ms = Column(Float, nullable=True)
    memory_used_mb = Column(Float, nullable=True)
    
    # Status
    success = Column(Boolean, default=True)
    error_message = Column(String(255), nullable=True)

    # Context
    resource_id = Column(String(36), nullable=True)
    batch_size = Column(Integer, nullable=True)  # For batch operations
    
    # Timestamp
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self):
        return (
            f"<PerfLog {self.component} {self.operation} "
            f"{self.duration_ms}ms {'✓' if self.success else '✗'}>"
        )
