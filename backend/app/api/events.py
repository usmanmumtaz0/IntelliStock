"""Verified inventory event endpoints with a single documented wire alias policy."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.event import InventoryEvent

router = APIRouter(prefix="/api/v1/events", tags=["events"])


class EventResponse(BaseModel):
    """Python uses snake_case; the JSON wire contract uses frontend-friendly aliases."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    zone: Optional[str]
    product: Optional[str]
    from_qty: Optional[int] = Field(default=None, alias="from")
    to_qty: Optional[int] = Field(default=None, alias="to")
    confidence: Optional[float]
    min_ago: int = Field(alias="minAgo")


def _quantity_from_state(state: str | None) -> int | None:
    if not state:
        return None
    match = re.fullmatch(r"qty=(-?\d+)", state.strip())
    return int(match.group(1)) if match else None


def _event_quantities(event: InventoryEvent) -> tuple[int | None, int | None]:
    previous = _quantity_from_state(event.previous_state)
    current = _quantity_from_state(event.new_state)
    if event.extra_data:
        try:
            extra = json.loads(event.extra_data)
            previous = extra.get("previous_quantity", extra.get("from_qty", previous))
            current = extra.get("new_quantity", extra.get("to_qty", current))
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
    return previous, current


def _serialize_event(event: InventoryEvent, now: datetime) -> EventResponse:
    previous, current = _event_quantities(event)
    min_ago = max(0, int((now - event.created_at).total_seconds() / 60)) if event.created_at else 0
    return EventResponse(
        id=event.id,
        zone=event.zone_id,
        product=event.product_id,
        from_qty=previous,
        to_qty=current,
        confidence=(event.confidence * 100) if event.confidence is not None else None,
        min_ago=min_ago,
    )


def _query_events(
    db: Session,
    *,
    zone_id: str | None = None,
    product_id: str | None = None,
    limit: int = 30,
) -> list[EventResponse]:
    query = db.query(InventoryEvent)
    if zone_id:
        query = query.filter(InventoryEvent.zone_id == zone_id)
    if product_id:
        query = query.filter(InventoryEvent.product_id == product_id)
    records = query.order_by(InventoryEvent.created_at.desc()).limit(limit).all()
    now = datetime.utcnow()
    return [_serialize_event(event, now) for event in records]


@router.get("", response_model=List[EventResponse])
def list_events(
    zone_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _query_events(db, zone_id=zone_id, product_id=product_id, limit=limit)


@router.get("/zone/{zone_id}", response_model=List[EventResponse])
def list_events_by_zone(
    zone_id: str,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _query_events(db, zone_id=zone_id, limit=limit)


@router.get("/product/{product_id}", response_model=List[EventResponse])
def list_events_by_product(
    product_id: str,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _query_events(db, product_id=product_id, limit=limit)
