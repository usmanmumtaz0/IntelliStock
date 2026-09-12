"""
Event publisher for Redis pub/sub.
"""
import json
import logging
from typing import Any, Dict
import redis

from app.core.config import settings
from app.models.event import EventType

logger = logging.getLogger(__name__)

# Redis client for pub/sub
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

INVENTORY_CHANNEL = "inventory.events"


def publish_event(
    event_type: EventType,
    camera_id: str | None = None,
    zone_id: str | None = None,
    product_id: str | None = None,
    previous_state: str | None = None,
    new_state: str | None = None,
    confidence: float | None = None,
    extra_data: Dict[str, Any] | None = None,
) -> bool:
    """
    Publish an inventory event to Redis pub/sub.
    
    Args:
        event_type: Type of event (EventType enum)
        camera_id: Camera UUID (optional)
        zone_id: Zone UUID (optional)
        product_id: Product UUID (optional)
        previous_state: Previous state value (optional)
        new_state: New state value (optional)
        confidence: Detection confidence 0.0-1.0 (optional)
        extra_data: Additional metadata as dict (optional)
    
    Returns:
        bool: True if published successfully
    """
    try:
        event_payload = {
            "event_type": event_type.value,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "camera_id": camera_id,
            "zone_id": zone_id,
            "product_id": product_id,
            "previous_state": previous_state,
            "new_state": new_state,
            "confidence": confidence,
            "extra_data": extra_data or {},
        }
        
        # Publish to Redis channel
        message = json.dumps(event_payload)
        result = redis_client.publish(INVENTORY_CHANNEL, message)
        
        if result > 0:
            logger.debug(f"Event published: {event_type.value} (subscribers: {result})")
            return True
        else:
            logger.debug(f"Event published but no subscribers: {event_type.value}")
            return True  # Still return True, event was published
    
    except Exception as e:
        logger.error(f"Failed to publish event {event_type.value}: {e}")
        return False


def publish_stock_updated(
    zone_id: str,
    product_id: str,
    quantity: int,
    confidence: float,
    camera_id: str | None = None,
) -> bool:
    """Publish a stock update event."""
    return publish_event(
        EventType.STOCK_UPDATED,
        camera_id=camera_id,
        zone_id=zone_id,
        product_id=product_id,
        new_state=f"qty={quantity}",
        confidence=confidence,
    )


def publish_low_stock(zone_id: str, product_id: str, quantity: int) -> bool:
    """Publish a low stock alert."""
    return publish_event(
        EventType.LOW_STOCK,
        zone_id=zone_id,
        product_id=product_id,
        new_state=f"qty={quantity}",
    )


def publish_out_of_stock(zone_id: str, product_id: str) -> bool:
    """Publish an out of stock alert."""
    return publish_event(
        EventType.OUT_OF_STOCK,
        zone_id=zone_id,
        product_id=product_id,
        new_state="qty=0",
    )


def publish_camera_offline(camera_id: str) -> bool:
    """Publish a camera offline event."""
    return publish_event(
        EventType.CAMERA_OFFLINE,
        camera_id=camera_id,
        new_state="offline",
    )


def publish_camera_online(camera_id: str) -> bool:
    """Publish a camera online event."""
    return publish_event(
        EventType.CAMERA_ONLINE,
        camera_id=camera_id,
        new_state="online",
    )
