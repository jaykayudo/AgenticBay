from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import (
    admin_router,
    agents_router,
    auth_router,
    marketplace_router,
    notifications_router,
    sessions_router,
    wallet_router,
    webhooks_router,
)
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import close_asyncpg_pool
from app.core.redis import close_redis
from app.websocket.orchestrator import router as ws_router
from app.websocket.user_agent_chat import router as user_agent_ws_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    from app.tasks.agent_health_tasks import health_check_all_agents_task
    from app.tasks.invoice_tasks import (
        expire_unpaid_invoices_task,
        reconcile_locked_wallets_task,
        sync_wallet_balances_task,
    )

    tasks = [
        asyncio.create_task(expire_unpaid_invoices_task()),
        asyncio.create_task(sync_wallet_balances_task()),
        asyncio.create_task(reconcile_locked_wallets_task()),
        asyncio.create_task(health_check_all_agents_task()),
    ]
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await close_redis()
        await close_asyncpg_pool()


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json" if not settings.is_production else None,
    docs_url=f"{settings.API_V1_PREFIX}/docs" if not settings.is_production else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(auth_router, prefix="/api")
app.include_router(agents_router, prefix="/api")
app.include_router(marketplace_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(wallet_router, prefix="/api")
app.include_router(webhooks_router, prefix="/api")
app.include_router(sessions_router, prefix="/api")
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(ws_router)
app.include_router(user_agent_ws_router)


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({"name": settings.APP_NAME, "status": "running"})
