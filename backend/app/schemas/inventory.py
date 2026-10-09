"""
Inventory schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.inventory import InventoryStatus


class InventoryResponse(BaseModel):
    """Schema for trusted inventory state responses."""

    id: str
    zone_id: str
    product_id: str
    sku: Optional[str] = None
    name: Optional[str] = None
    current_quantity: int = Field(..., ge=0)
    threshold: Optional[int] = Field(default=None, ge=0)
    status: InventoryStatus
    verified: bool
    pending_quantity: Optional[int] = Field(default=None, ge=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    last_observation_time: Optional[datetime] = None
    observations_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InventoryListResponse(BaseModel):
    """Schema for listing inventory with verified state and threshold context."""

    id: str
    zone_id: str
    product_id: str
    sku: Optional[str] = None
    name: Optional[str] = None
    current_quantity: int = Field(..., ge=0)
    threshold: Optional[int] = Field(default=None, ge=0)
    status: InventoryStatus
    verified: bool
    pending_quantity: Optional[int] = Field(default=None, ge=0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    last_observation_time: Optional[datetime] = None
    observations_count: int = Field(default=0, ge=0)
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
