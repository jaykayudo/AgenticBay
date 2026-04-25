from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


class UserWSClient:
    """Wraps the user's frontend FastAPI WebSocket with typed send methods."""

    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket

    async def send(self, payload: dict[str, Any]) -> None:
        await self.websocket.send_text(json.dumps(payload))

    async def close(self) -> None:
        try:
            await self.websocket.close()
        except Exception:
            pass
