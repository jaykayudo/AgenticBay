from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.redis import get_redis

router = APIRouter()


@router.get("")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/detailed")
async def detailed_health(db: AsyncSession = Depends(get_session)) -> dict[str, object]:
    checks: dict[str, str] = {"api": "ok", "database": "unknown", "redis": "unknown"}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    try:
        redis = await get_redis()
        await redis.ping()  # type: ignore[misc]
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
