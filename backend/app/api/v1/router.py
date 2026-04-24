from fastapi import APIRouter

from app.api.v1.endpoints import health, webhooks

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(webhooks.router, tags=["webhooks"])
