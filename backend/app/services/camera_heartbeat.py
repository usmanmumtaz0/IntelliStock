"""
Camera Heartbeat Service (INV-004)
Detects offline cameras via timeout and marks inventory as CAMERA_OFFLINE.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict

import redis
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.camera import Camera
from app.models.inventory import Inventory, InventoryStatus
from app.database import SessionLocal

logger = logging.getLogger(__name__)

# Redis client for heartbeat tracking
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

# Heartbeat prefix for Redis keys
HEARTBEAT_KEY_PREFIX = "camera:heartbeat:"

# How often to check for offline cameras (in seconds)
HEARTBEAT_CHECK_INTERVAL = 5


class CameraHeartbeatService:
    """Monitors camera heartbeat and marks cameras offline when timeout expires."""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def record_heartbeat(self, camera_id: str):
        """Record that a camera is alive (call from CV pipeline)."""
        key = f"{HEARTBEAT_KEY_PREFIX}{camera_id}"
        timestamp = datetime.utcnow().isoformat()
        redis_client.set(key, timestamp)
        logger.debug(f"Heartbeat recorded for camera {camera_id}")
    
    def start(self):
        """Start the heartbeat monitor thread."""
        if self.running:
            logger.warning("Heartbeat service already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("Camera heartbeat service started")
    
    def stop(self):
        """Stop the heartbeat monitor thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Camera heartbeat service stopped")
    
    def _monitor_loop(self):
        """Background thread: periodically check for offline cameras."""
        while self.running:
            try:
                self._check_offline_cameras()
            except Exception as e:
                logger.error(f"Error in heartbeat monitor loop: {e}")
            
            time.sleep(HEARTBEAT_CHECK_INTERVAL)
    
    def _check_offline_cameras(self):
        """Query all cameras and check if any have timed out."""
        db = SessionLocal()
        try:
            cameras = db.query(Camera).filter(Camera.is_active == True).all()
            
            for camera in cameras:
                key = f"{HEARTBEAT_KEY_PREFIX}{camera.id}"
                
                # Get last heartbeat
                last_heartbeat_str = redis_client.get(key)
                
                if last_heartbeat_str is None:
                    # No heartbeat recorded yet (camera just added or never came online)
                    continue
                
                # Parse timestamp
                try:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                except ValueError:
                    logger.warning(f"Invalid heartbeat timestamp for camera {camera.id}")
                    continue
                
                # Check if timed out
                time_since_heartbeat = datetime.utcnow() - last_heartbeat
                timeout_delta = timedelta(seconds=camera.offline_timeout_seconds)
                
                if time_since_heartbeat > timeout_delta:
                    # Camera is offline
                    self._mark_camera_offline(db, camera)
        finally:
            db.close()
    
    def _mark_camera_offline(self, db, camera: Camera):
        """Mark all inventory for this camera as CAMERA_OFFLINE."""
        try:
            # Find all inventory records that depend on this camera
            # (via zones that this camera monitors)
            inventory_records = db.query(Inventory).all()  # Simplified for MVP
            
            updated_count = 0
            for inv in inventory_records:
                if inv.status != InventoryStatus.CAMERA_OFFLINE:
                    prev_status = inv.status
                    inv.status = InventoryStatus.CAMERA_OFFLINE
                    updated_count += 1
                    
                    logger.info(
                        f"Camera {camera.id} offline: "
                        f"marked {inv.zone_id}/{inv.product_id} "
                        f"offline (was {prev_status.value})"
                    )
            
            if updated_count > 0:
                db.commit()
                logger.warning(
                    f"Camera {camera.id} marked offline; {updated_count} inventory records updated"
                )
        except Exception as e:
            logger.error(f"Failed to mark camera {camera.id} offline: {e}")
            db.rollback()


# Global service instance
_heartbeat_service: CameraHeartbeatService | None = None


def get_heartbeat_service() -> CameraHeartbeatService:
    """Get or create the global heartbeat service."""
    global _heartbeat_service
    if _heartbeat_service is None:
        _heartbeat_service = CameraHeartbeatService()
    return _heartbeat_service
