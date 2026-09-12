"""
Observation Window Service (INV-001)
Manages rolling window of recent observations per (camera, zone, product).
Uses Redis for fast, temporary storage. Only committed observations go to PostgreSQL.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client for observation windows
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Configuration
WINDOW_SIZE = 5  # Keep last N observations
WINDOW_TTL_SECONDS = 600  # Expire windows after 10 minutes of inactivity


class Observation:
    """Single observation of product quantity in a zone."""
    
    def __init__(
        self,
        zone_id: str,
        product_id: str,
        quantity: int,
        confidence: float,
        camera_id: str | None = None,
        timestamp: Optional[str] = None,
    ):
        self.zone_id = zone_id
        self.product_id = product_id
        self.quantity = quantity
        self.confidence = confidence
        self.camera_id = camera_id
        self.timestamp = timestamp or datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dict for Redis storage."""
        return {
            "zone_id": self.zone_id,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "confidence": self.confidence,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "Observation":
        """Create from dict."""
        return Observation(
            zone_id=data["zone_id"],
            product_id=data["product_id"],
            quantity=data["quantity"],
            confidence=data["confidence"],
            camera_id=data.get("camera_id"),
            timestamp=data.get("timestamp"),
        )


class ObservationWindow:
    """Manages observations for a specific (camera, zone, product)."""
    
    def __init__(self, camera_id: str, zone_id: str, product_id: str):
        self.camera_id = camera_id
        self.zone_id = zone_id
        self.product_id = product_id
        self.key = f"obs_window:{camera_id}:{zone_id}:{product_id}"
    
    def add_observation(self, observation: Observation) -> List[Observation]:
        """
        Add observation to window, maintain size limit.
        
        Returns:
            List of observations in the window (newest first)
        """
        # Get current window
        current = self._get_observations()
        
        # Add new observation
        current.insert(0, observation)
        
        # Keep only WINDOW_SIZE most recent
        current = current[:WINDOW_SIZE]
        
        # Store back to Redis
        self._store_observations(current)
        
        logger.debug(f"Observation added to window {self.key}: qty={observation.quantity}")
        return current
    
    def get_observations(self) -> List[Observation]:
        """Get all observations in current window."""
        return self._get_observations()
    
    def get_latest_observation(self) -> Optional[Observation]:
        """Get most recent observation."""
        obs = self._get_observations()
        return obs[0] if obs else None
    
    def get_quantity_consensus(self) -> Optional[int]:
        """
        Calculate consensus quantity from window observations.
        Uses majority voting or average depending on variance.
        """
        obs = self._get_observations()
        if not obs:
            return None
        
        quantities = [o.quantity for o in obs]
        
        # If all within 1 unit of each other, use average
        if max(quantities) - min(quantities) <= 1:
            return round(sum(quantities) / len(quantities))
        
        # Otherwise use median
        sorted_qty = sorted(quantities)
        mid = len(sorted_qty) // 2
        return sorted_qty[mid]
    
    def get_average_confidence(self) -> float:
        """Calculate average confidence of observations in window."""
        obs = self._get_observations()
        if not obs:
            return 0.0
        return sum(o.confidence for o in obs) / len(obs)
    
    def clear(self):
        """Clear the observation window."""
        redis_client.delete(self.key)
        logger.debug(f"Observation window cleared: {self.key}")
    
    def _get_observations(self) -> List[Observation]:
        """Get observations from Redis."""
        try:
            data = redis_client.lrange(self.key, 0, -1)
            observations = [Observation.from_dict(json.loads(item)) for item in data]
            return observations
        except Exception as e:
            logger.error(f"Failed to get observations from {self.key}: {e}")
            return []
    
    def _store_observations(self, observations: List[Observation]):
        """Store observations to Redis."""
        try:
            # Clear and rebuild
            redis_client.delete(self.key)
            for obs in observations:
                redis_client.rpush(self.key, json.dumps(obs.to_dict()))
            # Set expiration
            redis_client.expire(self.key, WINDOW_TTL_SECONDS)
        except Exception as e:
            logger.error(f"Failed to store observations to {self.key}: {e}")


def get_observation_window(camera_id: str, zone_id: str, product_id: str) -> ObservationWindow:
    """Get or create observation window for (camera, zone, product)."""
    return ObservationWindow(camera_id, zone_id, product_id)
