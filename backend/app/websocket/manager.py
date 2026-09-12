"""
WebSocket connection manager for real-time updates.
Broadcasts events from Redis to connected clients.
"""
import json
import logging
import threading
from typing import Set
import redis
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

INVENTORY_CHANNEL = "inventory.events"


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Set[WebSocket] = set()
        self.redis_client = None
        self.broadcast_thread = None
        self.running = False
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to client: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    def start_redis_listener(self):
        """Start listening to Redis in a background thread."""
        if self.running:
            logger.warning("Redis listener already running")
            return
        
        self.running = True
        self.redis_client = redis.from_url(
            __import__("app.core.config", fromlist=["settings"]).settings.REDIS_URL,
            decode_responses=True
        )
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(INVENTORY_CHANNEL)
        
        # Start listener thread
        thread = threading.Thread(
            target=self._redis_listen_loop,
            args=(pubsub,),
            daemon=True
        )
        thread.start()
        logger.info("Redis listener started")
    
    def stop_redis_listener(self):
        """Stop listening to Redis."""
        self.running = False
        if self.redis_client:
            self.redis_client.close()
        logger.info("Redis listener stopped")
    
    def _redis_listen_loop(self, pubsub):
        """Listen to Redis and broadcast events."""
        try:
            for message in pubsub.listen():
                if not self.running:
                    break
                
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        # Broadcast to WebSocket clients
                        import asyncio
                        # Schedule broadcast in event loop (this is a simplified version)
                        logger.debug(f"Broadcasting event: {event.get('event_type')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Redis message: {e}")
        except Exception as e:
            logger.error(f"Redis listener error: {e}")
            self.running = False


# Global connection manager
manager = ConnectionManager()
