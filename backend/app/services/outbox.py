"""Enqueue within the caller's transaction; never commit here."""
import json
from uuid import uuid4
from app.models.delivery import OutboxEvent


def enqueue(db, topic: str, payload: dict, event_id: str | None = None):
    event_id = event_id or str(uuid4())
    event = OutboxEvent(id=event_id, topic=topic,
                        payload=json.dumps({**payload, "event_id": event_id, "event_type": topic}))
    db.add(event)
    return event


def alert_changed(db, alert):
    db.flush()
    enqueue(db, "alert_updated", {"alert_id": alert.id, "zone_id": alert.zone_id,
                                 "product_id": alert.product_id, "status": alert.status.value})
