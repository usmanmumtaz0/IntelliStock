"""
Events endpoints for activity feed and reconciliation history.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.event import InventoryEvent

router = APIRouter(prefix="/api/v1/events", tags=["events"])


class EventResponse(BaseModel):
    id: str
    zone: str
    product: str
    from_qty: int
    to_qty: int
    confidence: float
    min_ago: int

    class Config:
        from_attributes = True


@router.get("", response_model=List[EventResponse])
def list_events(
    zone_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List verified reconciliation events (inventory state transitions).
    Events are ordered by recency.
    """
    query = db.query(InventoryEvent).order_by(InventoryEvent.created_at.desc())
    
    if zone_id:
        query = query.filter(InventoryEvent.zone_id == zone_id)
    if product_id:
        query = query.filter(InventoryEvent.product_id == product_id)
    
    events = query.limit(limit).all()
    now = datetime.utcnow()
    
    result = []
    for event in events:
        min_ago = int((now - event.created_at).total_seconds() / 60) if event.created_at else 0
        
        result.append(EventResponse(
            id=event.id,
            zone=event.zone_id,
            product=event.product_id,
            from_qty=0,  # TODO: parse from extra_data
            to_qty=0,    # TODO: parse from extra_data
            confidence=event.confidence * 100 if event.confidence else 90,
            min_ago=min_ago,
        ))
    
    return result


@router.get("/zone/{zone_id}", response_model=List[EventResponse])
def list_events_by_zone(
    zone_id: str,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent events for a specific zone."""
    events = db.query(InventoryEvent).filter(
        InventoryEvent.zone_id == zone_id
    ).order_by(InventoryEvent.created_at.desc()).limit(limit).all()
    
    now = datetime.utcnow()
    result = []
    for event in events:
        min_ago = int((now - event.created_at).total_seconds() / 60) if event.created_at else 0
        result.append(EventResponse(
            id=event.id,
            zone=event.zone_id,
            product=event.product_id,
            from_qty=0,
            to_qty=0,
            confidence=event.confidence * 100 if event.confidence else 90,
            min_ago=min_ago,
        ))
    
    return result


@router.get("/product/{product_id}", response_model=List[EventResponse])
def list_events_by_product(
    product_id: str,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent events for a specific product across all zones."""
    events = db.query(InventoryEvent).filter(
        InventoryEvent.product_id == product_id
    ).order_by(InventoryEvent.created_at.desc()).limit(limit).all()
    
    now = datetime.utcnow()
    result = []
    for event in events:
        min_ago = int((now - event.created_at).total_seconds() / 60) if event.created_at else 0
        result.append(EventResponse(
            id=event.id,
            zone=event.zone_id,
            product=event.product_id,
            from_qty=0,
            to_qty=0,
            confidence=event.confidence * 100 if event.confidence else 90,
            min_ago=min_ago,
        ))
    
    return result
