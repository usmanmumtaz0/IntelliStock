"""
Inventory history model — immutable append-only audit trail of quantity changes.
"""
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Text, Enum as SQLEnum, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from enum import Enum as PyEnum
from datetime import datetime


class InventoryChangeType(str, PyEnum):
    """Types of inventory changes."""
    INITIALIZATION = "INITIALIZATION"
    DETECTION = "DETECTION"
    RECONCILIATION = "RECONCILIATION"
    MANUAL_UPDATE = "MANUAL_UPDATE"
    RESTOCK = "RESTOCK"
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"
    CORRECTION = "CORRECTION"
    SYSTEM_UPDATE = "SYSTEM_UPDATE"
    MIGRATION = "MIGRATION"


class InventoryHistory(BaseModel):
    """Immutable append-only record of all inventory state changes."""

    __tablename__ = "inventory_history"

    # Inventory coordinates
    zone_id = Column(String(36), ForeignKey("shelf_zones.id"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False, index=True)

    # Quantity change
    previous_quantity = Column(Integer, nullable=False)
    new_quantity = Column(Integer, nullable=False)
    quantity_delta = Column(Integer, nullable=False)  # new - previous

    # Change metadata
    change_type = Column(SQLEnum(InventoryChangeType), nullable=False, index=True)
    confidence = Column(Float, default=0.0)  # 0.0-1.0

    # Source tracking
    source_system = Column(String(50), nullable=False, index=True)  # reconciliation, cv, manual
    source_id = Column(String(255), nullable=True)  # Reference to source event
    related_detection_id = Column(String(255), nullable=True)  # CV detection ID
    related_event_id = Column(String(255), nullable=True)  # Event ID

    # Actor tracking
    actor_user_id = Column(String(36), nullable=True)  # User who caused change
    actor_system = Column(String(100), nullable=True)  # System component

    # Context
    reason = Column(String(255), nullable=True)  # Human-readable why
    notes = Column(Text, nullable=True)  # Additional context

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    zone = relationship("ShelfZone")
    product = relationship("Product")

    def __repr__(self):
        return (
            f"<InventoryHistory {self.zone_id}/{self.product_id} "
            f"{self.previous_quantity}→{self.new_quantity} {self.change_type}>"
        )
