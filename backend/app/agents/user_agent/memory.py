from __future__ import annotations

import json
import logging
from typing import Any

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

_MEMORY_TTL = 60 * 60 * 24  # 24 hours


class SessionMemory:
    """
    Redis-backed conversation history for the LLM across turns.
    Key: user_agent_memory:{session_id}
    Value: JSON array of Anthropic message dicts.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._key = f"user_agent_memory:{session_id}"

    async def add_user_message(self, content: str) -> None:
        await self._append({"role": "user", "content": content})

    async def add_assistant_message(self, content: list[dict[str, Any]]) -> None:
        await self._append({"role": "assistant", "content": content})

    async def add_tool_result(self, tool_use_id: str, result: dict[str, Any]) -> None:
        await self._append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(result),
                    }
                ],
            }
        )

    async def add_system_context(self, context: str) -> None:
        """Inject an orchestrator event as a user-turn context block."""
        await self._append({"role": "user", "content": f"[SYSTEM CONTEXT] {context}"})

    async def get_messages_for_llm(self) -> list[dict[str, Any]]:
        redis = await get_redis()
        raw = await redis.get(self._key)
        if not raw:
            return []
        return json.loads(raw)  # type: ignore[no-any-return]

    async def clear(self) -> None:
        redis = await get_redis()
        await redis.delete(self._key)

    async def _append(self, message: dict[str, Any]) -> None:
        messages = await self.get_messages_for_llm()
        messages.append(message)
        redis = await get_redis()
        await redis.set(self._key, json.dumps(messages), ex=_MEMORY_TTL)
