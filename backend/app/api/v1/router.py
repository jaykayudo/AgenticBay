from fastapi import APIRouter

from app.api.v1.endpoints import agents, health, marketplace

api_router = APIRouter()

api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
