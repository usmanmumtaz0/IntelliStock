"""Persistent SMTP attempts, independent of inventory/event processing."""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from app.models.base import BaseModel


class NotificationDelivery(BaseModel):
    __tablename__ = "notification_deliveries"
    __table_args__ = (UniqueConstraint("alert_id", "alert_stage", "recipient", name="uq_notification_stage_recipient"),)
    alert_id = Column(String(36), ForeignKey("alerts.id"), nullable=False, index=True)
    alert_stage = Column(String(24), nullable=False)
    recipient = Column(String(255), nullable=False)
    status = Column(String(24), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    accepted_at = Column(DateTime, nullable=True)
    last_error = Column(String(100), nullable=True)
