"""
Inventory event model for audit trail.
"""
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text, Enum as SQLEnum
from app.models.base import BaseModel
from enum import Enum as PyEnum


class EventType(str, PyEnum):
    """Event types for inventory changes."""

    DETECTION_OBSERVED = "detection_observed"
    STOCK_UPDATED = "stock_updated"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    STOCK_REPLENISHED = "stock_replenished"
    ANOMALY_DETECTED = "anomaly_detected"
    CAMERA_ONLINE = "camera_online"
    CAMERA_OFFLINE = "camera_offline"
    PREDICTION_CREATED = "prediction_created"
    ALERT_CREATED = "alert_created"
    ALERT_RESOLVED = "alert_resolved"


class InventoryEvent(BaseModel):
    """Event log for all inventory state changes."""

    __tablename__ = "inventory_events"

    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    camera_id = Column(String(36), ForeignKey("cameras.id"), nullable=True)
    zone_id = Column(String(36), ForeignKey("shelf_zones.id"), nullable=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=True)
    
    previous_state = Column(String(64), nullable=True)
    new_state = Column(String(64), nullable=True)
    confidence = Column(Float, nullable=True)
    
    extra_data = Column(Text, nullable=True)  # JSON additional context

    def __repr__(self):
        return f"<InventoryEvent {self.event_type}>"
