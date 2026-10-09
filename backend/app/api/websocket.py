"""
WebSocket endpoint for real-time inventory updates.
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import validate_websocket_token
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/inventory")
async def websocket_inventory_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time inventory updates."""
    token = websocket.query_params.get("token") or websocket.headers.get("authorization")
    if not token:
        await websocket.close(code=4401)
        return

    if token.lower().startswith("bearer "):
        token = token[7:]

    if not validate_websocket_token(token):
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                logger.debug("WebSocket ping/pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        manager.disconnect(websocket)
        logger.error(f"WebSocket error: {exc}")


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
