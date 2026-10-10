"""
WebSocket connection manager for real-time updates.
Broadcasts events from Redis to connected clients.
"""
import json
import logging
import asyncio
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
        self.event_loop: asyncio.AbstractEventLoop | None = None
        self.stop_event = threading.Event()
    
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
        for connection in tuple(self.active_connections):
            try:
                await asyncio.wait_for(connection.send_json(message), timeout=2)
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
        
        try:
            self.event_loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error("WebSocket listener must start from the application event loop")
            return

        self.running = True
        self.stop_event.clear()
        self.redis_client = redis.from_url(
            __import__("app.core.config", fromlist=["settings"]).settings.REDIS_URL,
            decode_responses=True, socket_connect_timeout=1, socket_timeout=1
        )
        
        # Start listener thread
        thread = threading.Thread(
            target=self._reconnecting_listener,
            daemon=True
        )
        self.broadcast_thread = thread
        thread.start()
        logger.info("Redis listener started")
    
    def stop_redis_listener(self):
        """Stop listening to Redis."""
        self.running = False
        self.stop_event.set()
        if self.broadcast_thread and self.broadcast_thread.is_alive():
            self.broadcast_thread.join(timeout=3.0)
        if self.redis_client:
            self.redis_client.close()
        self.broadcast_thread = None
        self.event_loop = None
        logger.info("Redis listener stopped")

    def _reconnecting_listener(self):
        while not self.stop_event.is_set():
            try:
                with self.redis_client.pubsub() as pubsub:
                    pubsub.subscribe(INVENTORY_CHANNEL)
                    # Redis reconnection can have missed transient invalidations.
                    if self.event_loop and not self.event_loop.is_closed():
                        asyncio.run_coroutine_threadsafe(
                            self.broadcast({"event_type": "resync"}), self.event_loop)
                    while not self.stop_event.is_set():
                        message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
                        if message and message["type"] == "message":
                            try:
                                payload = json.loads(message["data"])
                            except (ValueError, TypeError):
                                continue
                            if self.event_loop and not self.event_loop.is_closed():
                                future = asyncio.run_coroutine_threadsafe(self.broadcast(payload), self.event_loop)
                                future.add_done_callback(self._log_broadcast_result)
            except redis.RedisError:
                logger.warning("Realtime Redis unavailable; retrying")
                self.stop_event.wait(2)

    @staticmethod
    def _log_broadcast_result(future):
        """Surface asynchronous broadcast failures from the Redis thread."""
        try:
            future.result()
        except Exception as exc:
            logger.error("WebSocket broadcast failed: %s", exc)


# Global connection manager
manager = ConnectionManager()
