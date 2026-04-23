from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.agent import AgentRegistrationRequest, AgentRegistrationResponse
from app.services.agent_registry import (
    AgentManifestFetchError,
    AgentRegistrationConflictError,
    AgentRegistryService,
)

router = APIRouter()


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
