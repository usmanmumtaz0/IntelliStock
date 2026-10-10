"""Durable delivery and explicit SKU-to-zone configuration."""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, UniqueConstraint
from app.models.base import BaseModel


class OutboxEvent(BaseModel):
    __tablename__ = "outbox_events"
    topic = Column(String(64), nullable=False)
    payload = Column(Text, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    available_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    last_error = Column(String(255), nullable=True)


class ZoneProductMapping(BaseModel):
    __tablename__ = "zone_product_mappings"
    __table_args__ = (UniqueConstraint("zone_id", "class_id", name="uq_zone_model_class"),)
    zone_id = Column(String(36), ForeignKey("shelf_zones.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    class_id = Column(Integer, nullable=False)
    # Enable only after validating an unobstructed fixed shelf ROI.
    allow_empty = Column(Boolean, nullable=False, default=False)
