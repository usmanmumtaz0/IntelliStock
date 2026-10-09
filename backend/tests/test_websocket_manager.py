"""WebSocket fan-out behavior independent of a live Redis server."""
import asyncio

from app.websocket.manager import ConnectionManager


class FakeSocket:
    def __init__(self, *, fails: bool = False):
        self.fails = fails
        self.messages: list[dict] = []

    async def send_json(self, message: dict):
        if self.fails:
            raise RuntimeError("connection closed")
        self.messages.append(message)


def test_broadcast_fans_out_and_removes_failed_connections():
    manager = ConnectionManager()
    connected = FakeSocket()
    disconnected = FakeSocket(fails=True)
    manager.active_connections = {connected, disconnected}
    event = {"type": "stock_updated", "data": {"zone_id": "zone-1"}}

    asyncio.run(manager.broadcast(event))

    assert connected.messages == [event]
    assert connected in manager.active_connections
    assert disconnected not in manager.active_connections
