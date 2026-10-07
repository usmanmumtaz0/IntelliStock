"""
Pydantic schemas for inventory history.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class InventoryHistoryBase(BaseModel):
    """Base history schema."""
    zone_id: str
    product_id: str
    previous_quantity: int
    new_quantity: int
    change_type: str
    confidence: float = 0.0
    source_system: str
    reason: Optional[str] = None


class InventoryHistoryCreate(InventoryHistoryBase):
    """Create new history record."""
    actor_user_id: Optional[str] = None
    actor_system: Optional[str] = None
    related_detection_id: Optional[str] = None
    related_event_id: Optional[str] = None
    notes: Optional[str] = None


class InventoryHistoryResponse(InventoryHistoryBase):
    """Return history record."""
    id: str
    quantity_delta: int
    created_at: datetime
    processed_at: datetime
    actor_user_id: Optional[str] = None
    actor_system: Optional[str] = None

    class Config:
        from_attributes = True


class TrendDataPoint(BaseModel):
    """Single point in trend data."""
    timestamp: datetime
    quantity: int
    changes_count: int
    avg_confidence: float
    min_qty: int
    max_qty: int


class InventoryHistoryPaginationResponse(BaseModel):
    """Paginated history response."""
    data: List[InventoryHistoryResponse]
    pagination: dict  # {total, limit, offset, pages}

    class Config:
        from_attributes = True


class DepletionMetric(BaseModel):
    """Depletion rate metric."""
    zone_id: str
    product_id: str
    rate_per_day: float
    total_depleted: int
    events: int
    date_range_days: int
