"""
Inventory schemas for request/response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.inventory import InventoryStatus


class InventoryResponse(BaseModel):
    """Schema for inventory state response."""

    id: str
    zone_id: str
    product_id: str
    quantity_estimate: int
    confidence: float
    status: InventoryStatus
    last_observation_time: Optional[str]
    observations_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    """Schema for listing inventory."""

    zone_id: str
    product_id: str
    quantity_estimate: int
    status: InventoryStatus
    confidence: float

    class Config:
        from_attributes = True
