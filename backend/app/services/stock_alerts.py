"""Deterministic alerts from committed inventory, never raw detections."""
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.alert import Alert, AlertStatus, AlertType, AlertSeverity
from app.models.inventory import Inventory, InventoryStatus
from app.models.product import Product
from app.services.outbox import alert_changed

ACTIVE = (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.IN_PROGRESS, AlertStatus.ESCALATED)
STOCK_TYPES = (AlertType.LOW_STOCK, AlertType.OUT_OF_STOCK)


def _description(alert_type, quantity, threshold):
    if alert_type == AlertType.OUT_OF_STOCK:
        return f"Committed inventory reached zero. Configured low-stock threshold: {threshold}."
    return f"Committed inventory is {quantity}, at or below the threshold of {threshold}."


def evaluate_committed_stock(db, payload):
    inv = db.query(Inventory).filter_by(
        zone_id=payload["zone_id"], product_id=payload["product_id"]
    ).with_for_update().first()
    if not inv:
        return
    state = inv.status.value
    if state in (
        InventoryStatus.UNKNOWN.value,
        InventoryStatus.DETECTION_UNCERTAIN.value,
        InventoryStatus.CAMERA_OFFLINE.value,
    ):
        return
    product = db.get(Product, inv.product_id)
    if not product:
        return

    quantity = inv.quantity_estimate
    threshold = product.low_stock_threshold
    desired = (
        AlertType.OUT_OF_STOCK
        if quantity == 0
        else AlertType.LOW_STOCK
        if quantity <= threshold
        else None
    )
    now = datetime.utcnow()
    active_alerts = db.query(Alert).filter(
        Alert.zone_id == inv.zone_id,
        Alert.product_id == inv.product_id,
        Alert.alert_type.in_(STOCK_TYPES),
        Alert.status.in_(ACTIVE),
    ).with_for_update().all()

    existing = None
    for alert in active_alerts:
        if alert.alert_type == desired:
            existing = alert
            continue
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = now
        alert.active_key = None
        alert.snoozed_until = None
        alert.current_quantity = quantity
        alert.threshold_value = threshold
        alert.related_event_id = payload.get("event_id")
        alert_changed(db, alert)

    if desired is None:
        return

    if existing:
        changed = (
            existing.current_quantity != quantity
            or existing.threshold_value != threshold
            or existing.related_event_id != payload.get("event_id")
        )
        if changed:
            existing.current_quantity = quantity
            existing.threshold_value = threshold
            existing.threshold_type = "low_stock"
            existing.description = _description(desired, quantity, threshold)
            existing.related_event_id = payload.get("event_id")
            existing.confidence = inv.confidence
            alert_changed(db, existing)
        return

    # A system-resolved alert proves the previous condition cleared or changed.
    # It must not suppress a new episode merely because it occurred within the
    # operator cooldown. Manually closed conditions retain the cooldown.
    recent = db.query(Alert).filter(
        Alert.zone_id == inv.zone_id,
        Alert.product_id == inv.product_id,
        Alert.alert_type == desired,
        Alert.created_at >= now - timedelta(seconds=settings.ALERT_COOLDOWN_SECONDS),
    ).order_by(Alert.created_at.desc()).first()
    if recent and not (
        recent.status == AlertStatus.RESOLVED and recent.resolved_by_user is None
    ):
        return

    title = "Out of stock" if desired == AlertType.OUT_OF_STOCK else "Low stock"
    alert = Alert(
        zone_id=inv.zone_id,
        product_id=inv.product_id,
        active_key=f"{inv.zone_id}:{inv.product_id}:{desired.value}",
        alert_type=desired,
        severity=AlertSeverity.HIGH if quantity == 0 else AlertSeverity.MEDIUM,
        status=AlertStatus.OPEN,
        title=title,
        description=_description(desired, quantity, threshold),
        recommendation="Restock immediately" if quantity == 0 else "Review inventory and replenish if required.",
        current_quantity=quantity,
        threshold_value=threshold,
        threshold_type="low_stock",
        confidence=inv.confidence,
        source_system="committed_inventory",
        related_event_id=payload.get("event_id"),
        created_by_system="stock_alert_worker",
    )
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
        if (
            alert.status == AlertStatus.OPEN
            and alert.created_at <= now - timedelta(seconds=settings.ALERT_ESCALATION_SECONDS)
        ):
            alert.status = AlertStatus.ESCALATED
            alert.severity = AlertSeverity.CRITICAL
            changed = True
        if changed:
            alert_changed(db, alert)