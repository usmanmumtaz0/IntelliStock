"""
Audit log model — track all state-changing operations for compliance and debugging.
"""
from datetime import datetime
from sqlalchemy import Column, DateTime, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
import uuid

from app.models.base import Base


class AuditLog(Base):
    """
    Audit log entry for tracking all state-changing operations.
    
    Columns:
        id: Unique audit log ID
        user_id: User performing the action
        action: Type of action (create, update, delete, login, logout)
        resource_type: Type of resource affected (product, camera, inventory, etc.)
        resource_id: ID of resource affected
        old_values: Previous values (for updates)
        new_values: New values (for creates/updates)
        ip_address: IP address of request
        user_agent: User agent of request
        status: Success or failure
        error_message: Error details if failed
        timestamp: When action occurred
    """
    __tablename__ = "audit_logs"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)  # create, update, delete, login, logout
    resource_type = Column(String(50), nullable=False, index=True)  # product, camera, inventory, etc.
    resource_id = Column(String(255), nullable=True, index=True)
    old_values = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)  # Previous state
    new_values = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)  # New state
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(Text, nullable=True)
    status = Column(String(20), default="success")  # success, failure
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return (
            f"<AuditLog(id={self.id}, user_id={self.user_id}, "
            f"action={self.action}, resource_type={self.resource_type}, "
            f"timestamp={self.timestamp})>"
        )
