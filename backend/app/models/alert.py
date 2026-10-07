"""
Alert model — system-generated notifications for inventory conditions.
Phase 9 Week 2: Alert Lifecycle & Analytics.
"""
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text, Enum as SQLEnum, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from enum import Enum as PyEnum
from datetime import datetime


class AlertType(str, PyEnum):
    """Types of alerts the system can generate."""
    LOW_STOCK = "LOW_STOCK"  # Qty <= low_stock_threshold
    OUT_OF_STOCK = "OUT_OF_STOCK"  # Qty = 0
    OVERSTOCK = "OVERSTOCK"  # Qty > max_stock_threshold
    ANOMALY = "ANOMALY"  # Unusual quantity change pattern
    DETECTION_FAILURE = "DETECTION_FAILURE"  # CV detection confidence too low
    STOCKOUT_RISK = "STOCKOUT_RISK"  # Predicted to stockout within N days
    PERFORMANCE_ISSUE = "PERFORMANCE_ISSUE"  # System latency or detection degradation
    RECONCILIATION_FAILED = "RECONCILIATION_FAILED"  # Observation window consensus failed
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"  # Manual update by user
    RESTOCKING_REQUIRED = "RESTOCKING_REQUIRED"  # Alert for staff to restock


class AlertSeverity(str, PyEnum):
    """Alert severity levels."""
    INFO = "INFO"  # Informational
    LOW = "LOW"  # Low priority
    MEDIUM = "MEDIUM"  # Medium priority
    HIGH = "HIGH"  # High priority, requires action
    CRITICAL = "CRITICAL"  # Critical, immediate action required


class AlertStatus(str, PyEnum):
    """Alert status/lifecycle."""
    OPEN = "OPEN"  # Newly created
    ACKNOWLEDGED = "ACKNOWLEDGED"  # User has seen it
    IN_PROGRESS = "IN_PROGRESS"  # Action being taken
    RESOLVED = "RESOLVED"  # Issue resolved
    DISMISSED = "DISMISSED"  # Acknowledged but no action needed
    ESCALATED = "ESCALATED"  # Escalated to higher priority
    EXPIRED = "EXPIRED"  # No longer relevant (time-based)


class Alert(BaseModel):
    """Alert record — immutable event log of system-generated notifications."""

    __tablename__ = "alerts"

    # Coordinates
    zone_id = Column(String(36), ForeignKey("shelf_zones.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)

    # Classification
    alert_type = Column(SQLEnum(AlertType), nullable=False, index=True)
    severity = Column(SQLEnum(AlertSeverity), nullable=False, index=True, default=AlertSeverity.MEDIUM)
    status = Column(SQLEnum(AlertStatus), nullable=False, index=True, default=AlertStatus.OPEN)

    # Content
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)  # Suggested action

    # Context
    current_quantity = Column(Integer, nullable=False)
    threshold_value = Column(Integer, nullable=True)  # Threshold that triggered alert
    threshold_type = Column(String(50), nullable=True)  # "low_stock", "high_stock", etc.

    # Metrics
    confidence = Column(Float, default=0.0)  # How confident is this alert? 0.0-1.0
    impact_score = Column(Float, default=0.0)  # Business impact 0.0-1.0

    # Source
    source_system = Column(String(100), nullable=False)  # "rule_engine", "cv_detection", "manual"
    related_event_id = Column(String(255), nullable=True)  # Reference to triggering event
    related_history_id = Column(String(36), ForeignKey("inventory_history.id"), nullable=True)

    # Lifecycle
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Auto-expire alerts after N days

    # Actor tracking
    created_by_system = Column(String(100), nullable=True)  # System component that created alert
    acknowledged_by_user = Column(String(36), nullable=True)  # User ID who acknowledged
    resolved_by_user = Column(String(36), nullable=True)  # User ID who resolved

    # Notifications
    notification_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime, nullable=True)
    notification_channels = Column(String(255), nullable=True)  # "email,sms,dashboard"

    # Relationships
    zone = relationship("ShelfZone")
    product = relationship("Product")
    history = relationship("InventoryHistory")

    def __repr__(self):
        return (
            f"<Alert {self.alert_type.value} {self.severity.value} "
            f"{self.zone_id}/{self.product_id} qty={self.current_quantity}>"
        )
