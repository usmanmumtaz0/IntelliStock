"""
Inventory model for trusted state tracking.
"""
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from enum import Enum as PyEnum


class InventoryStatus(str, PyEnum):
    """Inventory status states (state machine from architecture)."""

    UNKNOWN = "unknown"
    ADEQUATE = "adequate"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    DETECTION_UNCERTAIN = "detection_uncertain"
    CAMERA_OFFLINE = "camera_offline"


class Inventory(BaseModel):
    """Current inventory state per zone/product."""

    __tablename__ = "inventory"

    zone_id = Column(String(36), ForeignKey("shelf_zones.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    
    quantity_estimate = Column(Integer, default=0, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)  # 0.0-1.0
    status = Column(SQLEnum(InventoryStatus), default=InventoryStatus.UNKNOWN, nullable=False)
    
    # Tracking for reconciliation
    last_observation_time = Column(String(36), nullable=True)  # ISO timestamp
    observations_count = Column(Integer, default=0, nullable=False)

    zone = relationship("ShelfZone")
    product = relationship("Product")

    def __repr__(self):
        return f"<Inventory {self.zone_id}/{self.product_id} qty={self.quantity_estimate}>"
