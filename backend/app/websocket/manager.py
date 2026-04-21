import json
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # Maps connection_id -> WebSocket
        self._active: dict[str, WebSocket] = {}
        # Maps room_id -> set of connection_ids
        self._rooms: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, connection_id: str) -> None:
        await websocket.accept()
        self._active[connection_id] = websocket

    def disconnect(self, connection_id: str) -> None:
        self._active.pop(connection_id, None)
        for members in self._rooms.values():
            members.discard(connection_id)

    def join_room(self, connection_id: str, room_id: str) -> None:
        self._rooms.setdefault(room_id, set()).add(connection_id)

    def leave_room(self, connection_id: str, room_id: str) -> None:
        if room_id in self._rooms:
            self._rooms[room_id].discard(connection_id)

    async def send(self, connection_id: str, data: Any) -> None:
        ws = self._active.get(connection_id)
        if ws:
            payload = json.dumps(data) if not isinstance(data, str) else data
            await ws.send_text(payload)

    async def broadcast(self, data: Any) -> None:
        payload = json.dumps(data) if not isinstance(data, str) else data
        for ws in list(self._active.values()):
            await ws.send_text(payload)

    async def broadcast_to_room(self, room_id: str, data: Any) -> None:
        payload = json.dumps(data) if not isinstance(data, str) else data
        members = self._rooms.get(room_id, set())
        for cid in list(members):
            ws = self._active.get(cid)
            if ws:
                await ws.send_text(payload)

    @property
    def connection_count(self) -> int:
        return len(self._active)


manager = ConnectionManager()
