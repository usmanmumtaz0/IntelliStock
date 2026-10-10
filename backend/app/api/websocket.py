"""
WebSocket endpoint for real-time inventory updates.
"""
import logging
import asyncio

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
            if not await asyncio.to_thread(validate_websocket_token, token):
                await websocket.close(code=4401)
                break
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=15)
            except asyncio.TimeoutError:
                continue
            if data == "ping":
                await websocket.send_text("pong")
                logger.debug("WebSocket ping/pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        manager.disconnect(websocket)
        logger.error(f"WebSocket error: {exc}")
    finally:
        manager.disconnect(websocket)


# Listener startup/shutdown is owned by app.main.lifespan.
