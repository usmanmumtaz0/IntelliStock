"""
Pydantic schemas for alerts.
"""
from pydantic import BaseModel, field_serializer
from typing import List, Optional
from datetime import datetime, timezone


class AlertBase(BaseModel):
    """Base alert schema."""
    alert_type: str
    severity: str
    title: str
    current_quantity: int
    description: Optional[str] = None
    recommendation: Optional[str] = None


class AlertCreate(AlertBase):
    """Create alert."""
    zone_id: str
    product_id: str
    confidence: float = 1.0
    impact_score: float = 0.5


class AlertResponse(AlertBase):
    """Return alert."""
    id: str
    zone_id: str
    product_id: str
    status: str
    confidence: float
    impact_score: float
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    acknowledged_by_user: Optional[str] = None
    resolved_by_user: Optional[str] = None

    @field_serializer("snoozed_until")
    def serialize_snooze_time(self, value):
        if value is None:
            return None
        return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).isoformat()

    class Config:
        from_attributes = True


class AlertPaginationResponse(BaseModel):
    """Paginated alerts response."""
    data: List[AlertResponse]
    pagination: dict  # {total, limit, offset, pages}

    class Config:
        from_attributes = True


class AlertActionResponse(BaseModel):
    """Result of a persistent alert lifecycle mutation."""

    status: str
    alert_id: Optional[str] = None
    affected: int = 1
    message: str


class AlertStatsResponse(BaseModel):
    """Alert statistics."""
    total_alerts: int
    open_alerts: int
    critical: int
    high: int
    by_type: dict[str, int]
