"""
WebSocket endpoint for real-time inventory updates.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/inventory")
async def websocket_inventory_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time inventory updates.
    
    Clients connect and receive live events:
    - Stock updates
    - Low stock alerts
    - Out of stock alerts
    - Camera status changes
    
    Usage:
        ws://localhost:8000/ws/inventory
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            # Echo back or process client messages if needed
            if data == "ping":
                await websocket.send_text("pong")
                logger.debug("WebSocket ping/pong")
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    
    except Exception as e:
        manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}")


@router.on_event("startup")
async def startup_event():
    """Initialize WebSocket manager on app startup."""
    manager.start_redis_listener()
    logger.info("WebSocket manager initialized")


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup WebSocket manager on app shutdown."""
    manager.stop_redis_listener()
    logger.info("WebSocket manager cleaned up")
