"""
Audit service — comprehensive action logging and compliance tracking.
Phase 9 Week 3: Audit Trail system.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Manages audit logging for compliance and forensics."""

    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: str = None,
        user_id: str = None,
        old_values: dict = None,
        new_values: dict = None,
        ip_address: str = None,
        status: str = "success",
        error_message: str = None,
    ) -> AuditLog:
        """Log an audit action."""
        log = AuditLog(
            user_id=user_id or "system",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        self.db.commit()
        logger.info(
            f"Audit: {action} on {resource_type}/{resource_id} by {user_id}"
        )
        return log

    def log_inventory_update(
        self,
        resource_id: str,
        old_qty: int,
        new_qty: int,
        user_id: str = None,
    ) -> AuditLog:
        """Log inventory update."""
        return self.log_action(
            action="inventory_update",
            resource_type="inventory",
            resource_id=resource_id,
            user_id=user_id,
            old_values={"quantity": old_qty},
            new_values={"quantity": new_qty},
        )

    def log_alert_action(
        self,
        action: str,
        alert_id: str,
        user_id: str = None,
    ) -> AuditLog:
        """Log alert management action."""
        return self.log_action(
            action=action,
            resource_type="alert",
            resource_id=alert_id,
            user_id=user_id,
        )

    def log_config_change(
        self,
        config_type: str,
        resource_id: str,
        old_value: dict,
        new_value: dict,
        user_id: str = None,
    ) -> AuditLog:
        """Log configuration change."""
        return self.log_action(
            action=f"{config_type}_config_change",
            resource_type=config_type,
            resource_id=resource_id,
            user_id=user_id,
            old_values=old_value,
            new_values=new_value,
        )

    # Querying
    def get_logs_by_resource(
        self,
        resource_type: str,
        resource_id: str,
        days: int = 90,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[AuditLog], int]:
        """Get audit logs for a specific resource."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(AuditLog).filter(
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
            AuditLog.timestamp >= cutoff,
        )
        
        total = query.count()
        records = (
            query.order_by(desc(AuditLog.timestamp))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        return records, total

    def get_logs_by_user(
        self,
        user_id: str,
        days: int = 90,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[AuditLog], int]:
        """Get all actions by a user."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(AuditLog).filter(
            AuditLog.user_id == user_id,
            AuditLog.timestamp >= cutoff,
        )
        
        total = query.count()
        records = (
            query.order_by(desc(AuditLog.timestamp))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        return records, total

    def get_logs_by_action(
        self,
        action: str,
        days: int = 90,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[AuditLog], int]:
        """Get logs for a specific action type."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(AuditLog).filter(
            AuditLog.action == action,
            AuditLog.timestamp >= cutoff,
        )
        
        total = query.count()
        records = (
            query.order_by(desc(AuditLog.timestamp))
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        return records, total

    def get_failed_actions(
        self,
        days: int = 7,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get all failed actions (errors/failures)."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(AuditLog).filter(
            AuditLog.status == "failure",
            AuditLog.timestamp >= cutoff,
        ).order_by(desc(AuditLog.timestamp)).limit(limit).all()

    def cleanup_old_logs(self, retention_days: int = 180):
        """Delete audit logs older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        
        deleted = (
            self.db.query(AuditLog)
            .filter(AuditLog.timestamp < cutoff)
            .delete(synchronize_session=False)
        )
        
        self.db.commit()
        logger.info(f"Deleted {deleted} old audit logs")
        return deleted
