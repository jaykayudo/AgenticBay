from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.analytics import AgentAnalyticsResponse, AnalyticsRange
from app.schemas.agent import AgentRegistrationRequest, AgentRegistrationResponse
from app.services.agent_analytics import AgentAnalyticsNotFoundError, AgentAnalyticsService
from app.services.agent_registry import (
    AgentManifestFetchError,
    AgentRegistrationConflictError,
    AgentRegistryService,
)

router = APIRouter()


@router.get("/{agent_id}/analytics", response_model=AgentAnalyticsResponse)
async def get_agent_analytics(
    agent_id: str,
    range: AnalyticsRange = Query(default="30d"),
) -> AgentAnalyticsResponse:
    service = AgentAnalyticsService()

    try:
        return service.get_agent_analytics(agent_id=agent_id, range_key=range)
    except AgentAnalyticsNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/register",
    response_model=AgentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_agent(
    payload: AgentRegistrationRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> AgentRegistrationResponse:
    service = AgentRegistryService(db)

    try:
        agent, created = await service.register(payload)
    except AgentRegistrationConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AgentManifestFetchError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not created:
        response.status_code = status.HTTP_200_OK

    message = "Agent registered." if created else "Agent registration updated."
    return AgentRegistrationResponse(message=message, agent=agent)
