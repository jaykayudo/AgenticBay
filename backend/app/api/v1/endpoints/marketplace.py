from fastapi import APIRouter, HTTPException, status

from app.schemas.marketplace import (
    MarketplaceAgentInsightsResponse,
    MarketplaceSessionCreateRequest,
    MarketplaceSessionRead,
    MarketplaceStats,
)
from app.services.marketplace_public import (
    MarketplaceAgentNotFoundError,
    MarketplaceSessionNotFoundError,
    marketplace_public_service,
)

router = APIRouter()


@router.get("/stats", response_model=MarketplaceStats)
async def get_marketplace_stats() -> MarketplaceStats:
    """Return aggregate marketplace metrics for the public landing page."""
    return marketplace_public_service.get_stats()


@router.get("/agents/{agent_slug}/insights", response_model=MarketplaceAgentInsightsResponse)
async def get_marketplace_agent_insights(agent_slug: str) -> MarketplaceAgentInsightsResponse:
    """Return public marketplace reviews and performance stats for one agent."""
    try:
        return marketplace_public_service.get_agent_insights(agent_slug)
    except MarketplaceAgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/agents/{agent_slug}/sessions",
    response_model=MarketplaceSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_marketplace_session(
    agent_slug: str,
    payload: MarketplaceSessionCreateRequest,
) -> MarketplaceSessionRead:
    """Create a lightweight marketplace job session and return its redirect target."""
    try:
        return await marketplace_public_service.create_session(agent_slug, payload)
    except MarketplaceAgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/sessions/{session_id}", response_model=MarketplaceSessionRead)
async def get_marketplace_session(session_id: str) -> MarketplaceSessionRead:
    """Return the public session payload for the job session landing page."""
    try:
        return marketplace_public_service.get_session(session_id)
    except MarketplaceSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
