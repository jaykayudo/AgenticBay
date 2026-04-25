from __future__ import annotations

import logging
from typing import Any

from anthropic import AsyncAnthropic
from anthropic.types import Message

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"


class AgentLLM:
    def __init__(self) -> None:
        self._client: AsyncAnthropic | None = None

    def _get_client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic()
        return self._client

    async def call_with_tools(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str,
        max_tokens: int = 4096,
    ) -> Message:
        return await self._get_client().messages.create(
            model=_MODEL,
            max_tokens=max_tokens,
            system=system,
            tools=tools,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )
