"""Deterministic alerts from committed inventory, never raw detections."""
from datetime import datetime, timedelta
from sqlalchemy import or_
from app.core.config import settings
from app.models.alert import Alert, AlertStatus, AlertType, AlertSeverity
from app.models.inventory import Inventory, InventoryStatus
from app.models.product import Product
from app.services.outbox import alert_changed

ACTIVE = (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS, AlertStatus.ESCALATED)
STOCK_TYPES = (AlertType.LOW_STOCK, AlertType.OUT_OF_STOCK)


def evaluate_committed_stock(db, payload):
    inv = db.query(Inventory).filter_by(zone_id=payload["zone_id"],
                                        product_id=payload["product_id"]).with_for_update().first()
    if not inv:
        return
    state = payload.get("status", inv.status.value)
    if state in (InventoryStatus.UNKNOWN.value, InventoryStatus.DETECTION_UNCERTAIN.value,
                 InventoryStatus.CAMERA_OFFLINE.value):
        return
    product = db.get(Product, inv.product_id)
    if not product:
        return
    quantity = payload.get("quantity", inv.quantity_estimate)
    desired = (AlertType.OUT_OF_STOCK if quantity == 0 else
               AlertType.LOW_STOCK if state == InventoryStatus.LOW_STOCK.value else None)
    now = datetime.utcnow()
    alerts = db.query(Alert).filter(Alert.zone_id == inv.zone_id,
        Alert.product_id == inv.product_id, Alert.alert_type.in_(STOCK_TYPES),
        Alert.status.in_(ACTIVE)).with_for_update().all()
    existing = None
    for alert in alerts:
        if alert.alert_type == desired:
            existing = alert
        else:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = now
            alert.active_key = None
            alert.snoozed_until = None
            alert_changed(db, alert)
    if desired is None or existing:
        return
    recent = db.query(Alert).filter(Alert.zone_id == inv.zone_id,
        Alert.product_id == inv.product_id, Alert.alert_type == desired,
        Alert.created_at >= now - timedelta(seconds=settings.ALERT_COOLDOWN_SECONDS)).first()
    if recent:
        return
    alert = Alert(zone_id=inv.zone_id, product_id=inv.product_id,
        active_key=f"{inv.zone_id}:{inv.product_id}:{desired.value}",
        alert_type=desired, severity=AlertSeverity.HIGH if quantity == 0 else AlertSeverity.MEDIUM,
        status=AlertStatus.OPEN, title="Out of stock" if quantity == 0 else "Low stock",
        current_quantity=quantity, threshold_value=product.low_stock_threshold,
        confidence=payload.get("confidence", inv.confidence), source_system="committed_inventory",
        related_event_id=payload.get("event_id"))
    db.add(alert)
    alert_changed(db, alert)


def maintain_alerts(db, now=None):
    now = now or datetime.utcnow()
    alerts = db.query(Alert).filter(Alert.status.in_(ACTIVE)).with_for_update(skip_locked=True).all()
    for alert in alerts:
        if alert.snoozed_until and alert.snoozed_until > now:
            continue
        changed = False
        if alert.snoozed_until:
            alert.snoozed_until = None
            changed = True
        if (alert.status == AlertStatus.OPEN and
                alert.created_at <= now - timedelta(seconds=settings.ALERT_ESCALATION_SECONDS)):
            alert.status = AlertStatus.ESCALATED
            alert.severity = AlertSeverity.CRITICAL
            changed = True
        if changed:
            alert_changed(db, alert)
