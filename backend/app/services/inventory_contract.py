"""Map authoritative inventory plus transient observations to the API contract."""
from __future__ import annotations

from datetime import datetime

from app.models.inventory import Inventory, InventoryStatus
from app.services.observation_window import get_observation_window
from app.services.reconciliation import MIN_CONFIDENCE_THRESHOLD, MIN_CONSECUTIVE_FRAMES

VERIFIED_STATES = {
    InventoryStatus.ADEQUATE,
    InventoryStatus.LOW_STOCK,
    InventoryStatus.OUT_OF_STOCK,
}


def _as_datetime(value: datetime | str | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _pending_quantity(item: Inventory) -> int | None:
    """Return a differing, uncommitted Redis observation when one exists."""
    if item.zone is None or not item.zone.camera_id:
        return None
    latest = get_observation_window(item.zone.camera_id, item.zone_id, item.product_id).get_latest_observation()
    if latest is None or latest.quantity == item.quantity_estimate:
        return None
    return latest.quantity


def serialize_inventory(item: Inventory) -> dict:
    """Serialize trusted state without treating a CV observation as truth."""
    product = item.product
    verified = (
        item.status in VERIFIED_STATES
        and item.confidence >= MIN_CONFIDENCE_THRESHOLD
        and item.observations_count >= MIN_CONSECUTIVE_FRAMES
        and item.last_observation_time is not None
    )
    return {
        "id": item.id,
        "zone_id": item.zone_id,
        "product_id": item.product_id,
        "sku": product.sku if product else None,
        "name": product.name if product else None,
        "current_quantity": item.quantity_estimate,
        "threshold": product.low_stock_threshold if product else None,
        "status": item.status,
        "verified": verified,
        "pending_quantity": _pending_quantity(item),
        "confidence": item.confidence,
        "updated_at": item.updated_at,
        "created_at": item.created_at,
        "last_observation_time": _as_datetime(item.last_observation_time),
        "observations_count": item.observations_count,
    }
