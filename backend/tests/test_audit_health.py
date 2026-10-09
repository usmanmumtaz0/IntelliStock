"""
Tests for Phase 9 Week 3: Audit Trail and Health Monitoring.
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.database.connection import init_db
from app.services.audit_service import AuditService
from app.services.health_monitor import HealthMonitor
from app.models.audit_log import AuditLog
from app.models.system_health import SystemHealthMetric, PerformanceLog, ComponentStatus, HealthCheckType


@pytest.fixture
def db():
    """Initialize database and return session."""
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class TestAuditService:
    """Test audit service functionality."""

    def test_log_action(self, db: Session):
        """Test logging an action."""
        service = AuditService(db)
        
        log = service.log_action(
            action="test_action",
            resource_type="test",
            resource_id="test-123",
            user_id="user-001",
        )
        
        assert log is not None
        assert log.action == "test_action"
        assert log.resource_type == "test"
        assert log.user_id == "user-001"

    def test_log_inventory_update(self, db: Session):
        """Test logging inventory update."""
        service = AuditService(db)
        
        log = service.log_inventory_update(
            resource_id="inv-001",
            old_qty=5,
            new_qty=10,
            user_id="user-001",
        )
        
        assert log.action == "inventory_update"
        assert log.old_values == {"quantity": 5}
        assert log.new_values == {"quantity": 10}

    def test_log_config_change(self, db: Session):
        """Test logging configuration change."""
        service = AuditService(db)
        
        log = service.log_config_change(
            config_type="zone",
            resource_id="zone-001",
            old_value={"name": "Zone A"},
            new_value={"name": "Zone B"},
            user_id="user-001",
        )
        
        assert log.action == "zone_config_change"
        assert log.old_values == {"name": "Zone A"}

    def test_get_logs_by_user(self, db: Session):
        """Test querying logs by user."""
        service = AuditService(db)
        user_id = str(uuid4())
        
        # Create multiple logs
        for i in range(3):
            service.log_action(
                action=f"action_{i}",
                resource_type="test",
                resource_id=f"test-{i}",
                user_id=user_id,
            )
        
        records, total = service.get_logs_by_user(user_id=user_id, days=90)
        
        assert total >= 3
        assert all(r.user_id == user_id for r in records)

    def test_get_logs_by_resource(self, db: Session):
        """Test querying logs by resource."""
        service = AuditService(db)
        
        # Create logs for same resource
        for i in range(2):
            service.log_action(
                action=f"action_{i}",
                resource_type="inventory",
                resource_id="inv-001",
                user_id=str(uuid4()),
            )
        
        records, total = service.get_logs_by_resource(
            resource_type="inventory",
            resource_id="inv-001",
            days=90,
        )
        
        assert total >= 2
        assert all(r.resource_id == "inv-001" for r in records)

    def test_get_failed_actions(self, db: Session):
        """Test querying failed actions."""
        service = AuditService(db)
        
        # Create failed log
        failed_log = AuditLog(
            user_id="user-001",
            action="failed_action",
            resource_type="test",
            resource_id="test-001",
            status="failure",
            error_message="Something went wrong",
        )
        db.add(failed_log)
        db.commit()
        
        records = service.get_failed_actions(days=7)
        
        assert len(records) >= 1
        assert any(r.status == "failure" for r in records)

    def test_cleanup_old_logs(self, db: Session):
        """Test cleanup of old audit logs."""
        service = AuditService(db)
        
        # Create old log
        old_log = AuditLog(
            user_id="user-001",
            action="old_action",
            resource_type="test",
            resource_id="test-001",
            status="success",
        )
        old_log.timestamp = datetime.utcnow() - timedelta(days=200)
        db.add(old_log)
        
        # Create recent log
        service.log_action(
            action="recent_action",
            resource_type="test",
            resource_id="test-002",
            user_id="user-001",
        )
        
        db.commit()
        
        deleted = service.cleanup_old_logs(retention_days=90)
        
        assert deleted >= 1


class TestHealthMonitor:
    """Test health monitoring functionality."""

    def test_check_database_health(self, db: Session):
        """Test database health check."""
        monitor = HealthMonitor(db)
        result = monitor.check_database_health()
        
        assert "component" in result
        assert "status" in result
        assert result["is_healthy"] is not None

    def test_check_redis_health(self, db: Session):
        """Test Redis health check."""
        monitor = HealthMonitor(db)
        result = monitor.check_redis_health()
        
        assert "component" in result
        assert "status" in result
        assert "response_time_ms" in result

    def test_record_performance(self, db: Session):
        """Test recording performance metric."""
        monitor = HealthMonitor(db)
        
        log = monitor.record_performance(
            component="reconciliation",
            operation="reconcile_observation",
            duration_ms=125.5,
            success=True,
        )
        
        assert log is not None
        assert log.component == "reconciliation"
        assert log.duration_ms == 125.5
        assert log.success is True

    def test_get_performance_stats(self, db: Session):
        """Test getting performance statistics."""
        monitor = HealthMonitor(db)
        
        # Record multiple operations
        for i in range(5):
            monitor.record_performance(
                component=f"test_{id(monitor)}",
                operation=f"test_op_{id(monitor)}",
                duration_ms=100 + (i * 10),
                success=True,
            )
        
        stats = monitor.get_performance_stats(
            component=f"test_{id(monitor)}",
            operation=f"test_op_{id(monitor)}",
            days=7,
        )
        
        assert stats["count"] >= 5
        assert stats["avg_duration_ms"] > 0
        assert stats["success_rate"] == 1.0

    def test_get_system_health(self, db: Session):
        """Test getting overall system health."""
        monitor = HealthMonitor(db)
        
        # Do some health checks
        monitor.check_database_health()
        monitor.check_redis_health()
        
        health = monitor.get_system_health()
        
        assert "status" in health
        assert "components" in health
        assert health["status"] in ["HEALTHY", "DEGRADED", "UNKNOWN"]

    def test_get_performance_issues(self, db: Session):
        """Test detecting slow operations."""
        monitor = HealthMonitor(db)
        
        # Record slow operation
        monitor.record_performance(
            component="slow",
            operation="slow_query",
            duration_ms=5000,
            success=True,
        )
        
        issues = monitor.get_recent_performance_issues(
            threshold_ms=1000,
            days=7,
        )
        
        assert len(issues) >= 1
        assert issues[0].duration_ms >= 1000

    def test_get_failed_operations(self, db: Session):
        """Test getting failed operations."""
        monitor = HealthMonitor(db)
        
        # Record failed operation
        monitor.record_performance(
            component="test",
            operation="failing_op",
            duration_ms=500,
            success=False,
            error_message="Test error",
        )
        
        failures = monitor.get_failed_operations(days=7)
        
        assert len(failures) >= 1
        assert failures[0].success is False

    def test_cleanup_old_metrics(self, db: Session):
        """Test cleanup of old performance logs."""
        monitor = HealthMonitor(db)
        
        # Create old metric
        old_metric = PerformanceLog(
            component="old",
            operation="old_op",
            duration_ms=100,
            success=True,
        )
        old_metric.recorded_at = datetime.utcnow() - timedelta(days=100)
        db.add(old_metric)
        
        # Create recent metric
        monitor.record_performance(
            component="recent",
            operation="recent_op",
            duration_ms=100,
            success=True,
        )
        
        db.commit()
        
        deleted = monitor.cleanup_old_metrics(retention_days=90)
        
        assert deleted >= 1
