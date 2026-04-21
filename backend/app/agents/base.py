import asyncio
import uuid
from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any


class AgentStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BaseAgent(ABC):
    def __init__(self, agent_id: str | None = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.status = AgentStatus.IDLE
        self._task: asyncio.Task[None] | None = None

    @abstractmethod
    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute the agent logic."""
        ...

    async def start(self, input_data: dict[str, Any]) -> None:
        self.status = AgentStatus.RUNNING
        try:
            result = await self.run(input_data)
            self.status = AgentStatus.COMPLETED
            await self.on_complete(result)
        except asyncio.CancelledError:
            self.status = AgentStatus.CANCELLED
            raise
        except Exception as e:
            self.status = AgentStatus.FAILED
            await self.on_error(e)
            raise

    async def cancel(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            self.status = AgentStatus.CANCELLED

    async def on_complete(self, result: dict[str, Any]) -> None:
        pass

    async def on_error(self, error: Exception) -> None:
        pass
