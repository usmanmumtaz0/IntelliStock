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

    async def close(self, code):
        self.closed_code = code


def test_broadcast_fans_out_and_removes_failed_connections(monkeypatch):
    monkeypatch.setattr("app.core.security.validate_websocket_token", lambda token: token == "valid")
    manager = ConnectionManager()
    connected = FakeSocket()
    disconnected = FakeSocket(fails=True)
    manager.active_connections = {connected, disconnected}
    manager.connection_tokens = {connected: "valid", disconnected: "valid"}
    event = {"type": "stock_updated", "data": {"zone_id": "zone-1"}}

    asyncio.run(manager.broadcast(event))

    assert connected.messages == [event]
    assert connected in manager.active_connections
    assert disconnected not in manager.active_connections


def test_broadcast_tolerates_connection_set_changes(monkeypatch):
    monkeypatch.setattr("app.core.security.validate_websocket_token", lambda token: token == "valid")
    manager = ConnectionManager()

    class ChangingSocket(FakeSocket):
        async def send_json(self, message):
            manager.active_connections.clear()
            await super().send_json(message)

    changing = ChangingSocket()
    other = FakeSocket()
    manager.active_connections = {changing, other}
    manager.connection_tokens = {changing: "valid", other: "valid"}
    asyncio.run(manager.broadcast({"event_type": "resync"}))
    assert changing.messages and other.messages


def test_revoked_socket_does_not_receive_next_event(monkeypatch):
    monkeypatch.setattr("app.core.security.validate_websocket_token", lambda token: False)
    manager = ConnectionManager()
    socket = FakeSocket()
    manager.active_connections = {socket}
    manager.connection_tokens = {socket: "revoked"}
    asyncio.run(manager.broadcast({"event_type": "resync"}))
    assert socket.messages == []
    assert socket.closed_code == 4401
    assert socket not in manager.active_connections
