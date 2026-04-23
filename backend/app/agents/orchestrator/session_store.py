# orchestrator/session_store.py
import json
import redis.asyncio as aioredis
from app.agents.orchestrator.schema import JobSessionState

REDIS_URL      = "redis://localhost:6379"
SESSION_TTL    = 60 * 60 * 24  # 24 hours

class SessionStore:

    def __init__(self):
        self.redis = aioredis.from_url(REDIS_URL, decode_responses=True)

    async def save(self, state: JobSessionState) -> None:
        await self.redis.set(
            f"session:{state.session_id}",
            state.model_dump_json(),
            ex=SESSION_TTL
        )

    async def get(self, session_id: str) -> JobSessionState | None:
        raw = await self.redis.get(f"session:{session_id}")
        if not raw:
            return None
        return JobSessionState.model_validate_json(raw)

    async def delete(self, session_id: str) -> None:
        await self.redis.delete(f"session:{session_id}")