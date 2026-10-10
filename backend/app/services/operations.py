"""Transactional operator actions. Callers own the commit."""
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from app.models.audit_log import AuditLog
from app.models.inventory import Inventory, InventoryStatus
from app.models.inventory_history import InventoryHistory, InventoryChangeType
from app.models.event import InventoryEvent, EventType
from app.models.zone import ShelfZone
from app.services.outbox import enqueue


def audit(db, user, action, resource_type, resource_id, old=None, new=None):
    db.add(AuditLog(user_id=user.id, action=action, resource_type=resource_type,
                    resource_id=resource_id, old_values=old, new_values=new))


def stock_state(quantity, threshold):
    return (InventoryStatus.OUT_OF_STOCK if quantity == 0 else
            InventoryStatus.LOW_STOCK if quantity <= threshold else InventoryStatus.ADEQUATE)


def stock_changed(db, inv, event_id=None, confidence=None):
    enqueue(db, "stock_updated", {"camera_id": inv.zone.camera_id,
        "zone_id": inv.zone_id, "product_id": inv.product_id,
        "quantity": inv.quantity_estimate, "confidence": inv.confidence if confidence is None else confidence,
        "status": inv.status.value}, event_id=event_id)


def correct_inventory(db, inventory_id, data, user):
    # Match the vision writer's lock order: shelf, then inventory.
    zone_id = db.query(Inventory.zone_id).filter_by(id=inventory_id).scalar()
    if zone_id is None:
        raise HTTPException(404, "Inventory not found")
    db.query(ShelfZone).filter_by(id=zone_id).with_for_update().one()
    inv = db.query(Inventory).filter_by(id=inventory_id).populate_existing().with_for_update().one()
    expected = data.expected_updated_at
    if expected.tzinfo:
        expected = expected.astimezone(timezone.utc).replace(tzinfo=None)
    if inv.updated_at != expected:
        raise HTTPException(409, "Inventory changed. Refresh and review the current count before retrying.")
    previous = inv.quantity_estimate
    event_id = str(uuid4())
    inv.quantity_estimate = data.quantity
    inv.status = stock_state(data.quantity, inv.product.low_stock_threshold)
    # A human correction must not fabricate camera observations or confidence.
    inv.observations_count = 0
    inv.updated_at = datetime.utcnow()
    db.add(InventoryHistory(zone_id=inv.zone_id, product_id=inv.product_id,
        previous_quantity=previous, new_quantity=data.quantity,
        quantity_delta=data.quantity - previous, change_type=InventoryChangeType.CORRECTION,
        confidence=0, source_system="manual", actor_user_id=user.id,
        reason=data.reason, related_event_id=event_id))
    db.add(InventoryEvent(id=event_id, event_type=EventType.STOCK_UPDATED,
        camera_id=inv.zone.camera_id, zone_id=inv.zone_id, product_id=inv.product_id,
        previous_state=f"qty={previous}", new_state=f"qty={data.quantity}", confidence=0,
        extra_data=json.dumps({"previous_quantity": previous, "new_quantity": data.quantity,
                               "source": "manual"})))
    audit(db, user, "correct", "inventory", inv.id, {"quantity": previous},
          {"quantity": data.quantity, "reason": data.reason})
    stock_changed(db, inv, event_id, confidence=0)
    return inv
