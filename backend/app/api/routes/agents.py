from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_access_token
from app.api.deps import get_session
from app.auth.jwt import AccessTokenPayload
from app.models.agents import Agent, AgentStatus
from app.models.users import User, UserStatus
from app.services.agent_service import (
    AgentConflictError,
    AgentImageUploadError,
    AgentNotFoundError,
    AgentOwnershipError,
    AgentService,
    AgentServiceError,
    AgentWalletProvisionError,
)
from app.services.agent_validator import AgentValidationError
from app.services.vector_service import AgentVectorIndexError

router = APIRouter(prefix="/agents", tags=["agents"])


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class AgentActionInput(APIModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")
    price_usdc: Decimal | None = Field(default=None, ge=0, alias="priceUsdc")


class AgentSubmitRequest(APIModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str | None = Field(default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(min_length=1)
    base_url: AnyHttpUrl = Field(alias="baseUrl")
    source_code_url: AnyHttpUrl | None = Field(default=None, alias="sourceCodeUrl")
    profile_image_url: AnyHttpUrl | None = Field(default=None, alias="profileImageUrl")
    profile_image_data: str | None = Field(default=None, alias="profileImageData")
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    pricing_summary: dict[str, Any] = Field(default_factory=dict, alias="pricingSummary")
    actions: list[AgentActionInput] = Field(default_factory=list)


class AgentUpdateRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1)
    base_url: AnyHttpUrl | None = Field(default=None, alias="baseUrl")
    source_code_url: AnyHttpUrl | None = Field(default=None, alias="sourceCodeUrl")
    profile_image_url: AnyHttpUrl | None = Field(default=None, alias="profileImageUrl")
    profile_image_data: str | None = Field(default=None, alias="profileImageData")
    categories: list[str] | None = None
    tags: list[str] | None = None
    pricing_summary: dict[str, Any] | None = Field(default=None, alias="pricingSummary")


class AgentValidateRequest(APIModel):
    base_url: AnyHttpUrl = Field(alias="baseUrl")


class AgentStatusUpdateRequest(APIModel):
    status: AgentStatus


class AgentActionRead(APIModel):
    id: UUID
    name: str
    description: str
    input_schema: dict[str, Any] = Field(alias="inputSchema")
    output_schema: dict[str, Any] = Field(alias="outputSchema")
    price_usdc: Decimal | None = Field(alias="priceUsdc")
    is_active: bool = Field(alias="isActive")


class AgentRead(APIModel):
    id: UUID
    owner_id: UUID = Field(alias="ownerId")
    name: str
    slug: str
    description: str
    profile_image_url: str | None = Field(alias="profileImageUrl")
    base_url: str = Field(alias="baseUrl")
    source_code_url: str | None = Field(alias="sourceCodeUrl")
    status: AgentStatus
    categories: list[Any]
    tags: list[Any]
    wallet_address: str | None = Field(alias="walletAddress")
    circle_wallet_id: str | None = Field(alias="circleWalletId")
    orchestrator_api_key: str = Field(alias="orchestratorApiKey")
    embedding_id: str | None = Field(alias="embeddingId")
    capabilities_cache: dict[str, Any] | None = Field(alias="capabilitiesCache")
    pricing_summary: dict[str, Any] = Field(alias="pricingSummary")
    total_jobs: int = Field(alias="totalJobs")
    success_rate: Decimal = Field(alias="successRate")
    avg_rating: Decimal = Field(alias="avgRating")
    total_earned: Decimal = Field(alias="totalEarned")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    actions: list[AgentActionRead] = Field(default_factory=list)


class AgentValidationResponse(APIModel):
    ok: bool
    base_url: str = Field(alias="baseUrl")
    test_session_id: str = Field(alias="testSessionId")
    capabilities: dict[str, Any]
    invoke_response: Any = Field(alias="invokeResponse")


class AgentWalletResponse(APIModel):
    agent_id: UUID = Field(alias="agentId")
    circle_wallet_id: str = Field(alias="circleWalletId")
    wallet_address: str = Field(alias="walletAddress")


async def get_active_user(
    token: AccessTokenPayload = Depends(get_current_access_token),
    db: AsyncSession = Depends(get_session),
) -> User:
    try:
        user_id = UUID(token.sub)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token subject is invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await db.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current user could not be found or is not active.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def serialize_agent(agent: Agent) -> AgentRead:
    return AgentRead(
        id=agent.id,
        ownerId=agent.owner_id,
        name=agent.name,
        slug=agent.slug,
        description=agent.description,
        profileImageUrl=agent.profile_image_url,
        baseUrl=agent.base_url,
        sourceCodeUrl=agent.source_code_url,
        status=agent.status,
        categories=agent.categories,
        tags=agent.tags,
        walletAddress=agent.wallet_address,
        circleWalletId=agent.circle_wallet_id,
        orchestratorApiKey=agent.orchestrator_api_key,
        embeddingId=agent.embedding_id,
        capabilitiesCache=agent.capabilities_cache,
        pricingSummary=agent.pricing_summary,
        totalJobs=agent.total_jobs,
        successRate=agent.success_rate,
        avgRating=agent.avg_rating,
        totalEarned=agent.total_earned,
        createdAt=agent.created_at,
        updatedAt=agent.updated_at,
        actions=[
            AgentActionRead(
                id=action.id,
                name=action.name,
                description=action.description,
                inputSchema=action.input_schema,
                outputSchema=action.output_schema,
                priceUsdc=action.price,
                isActive=action.is_active,
            )
            for action in agent.actions
        ],
    )


def map_service_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AgentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, AgentOwnershipError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    if isinstance(exc, AgentConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, AgentValidationError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, (AgentWalletProvisionError, AgentVectorIndexError, AgentImageUploadError)):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    if isinstance(exc, AgentServiceError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Agent operation failed."
    )


@router.get("/mine", response_model=list[AgentRead])
async def list_my_agents(
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> list[AgentRead]:
    agents = await AgentService(db).list_owner_agents(current_user)
    return [serialize_agent(agent) for agent in agents]


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def submit_agent(
    payload: AgentSubmitRequest,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await AgentService(db).submit_agent(current_user, payload)
        return serialize_agent(agent)
    except Exception as exc:
        raise map_service_error(exc) from exc


@router.post("/validate", response_model=AgentValidationResponse)
async def validate_agent(
    payload: AgentValidateRequest,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> AgentValidationResponse:
    del current_user
    try:
        result = await AgentService(db).validate_base_url(str(payload.base_url))
        return AgentValidationResponse(
            ok=True,
            baseUrl=result.base_url,
            testSessionId=result.test_session_id,
            capabilities=result.capabilities,
            invokeResponse=result.invoke_response,
        )
    except Exception as exc:
        raise map_service_error(exc) from exc


@router.get("/{agent_id}", response_model=AgentRead)
async def get_agent_detail(
    agent_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await AgentService(db).get_agent(agent_id)
        return serialize_agent(agent)
    except Exception as exc:
        raise map_service_error(exc) from exc


@router.patch("/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: UUID,
    payload: AgentUpdateRequest,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await AgentService(db).update_agent(current_user, agent_id, payload)
        return serialize_agent(agent)
    except Exception as exc:
        raise map_service_error(exc) from exc


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> Response:
    try:
        await AgentService(db).delete_agent(current_user, agent_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as exc:
        raise map_service_error(exc) from exc


@router.patch("/{agent_id}/status", response_model=AgentRead)
async def update_agent_status(
    agent_id: UUID,
    payload: AgentStatusUpdateRequest,
    current_user: User = Depends(get_active_user),
    db: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await AgentService(db).set_status(current_user, agent_id, payload.status)
        return serialize_agent(agent)
    except Exception as exc:
        raise map_service_error(exc) from exc


@router.get("/{agent_id}/wallet", response_model=AgentWalletResponse)
async def get_agent_wallet(
    agent_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> AgentWalletResponse:
    try:
        wallet = await AgentService(db).get_wallet(agent_id)
        return AgentWalletResponse(
            agentId=agent_id,
            circleWalletId=wallet.circle_wallet_id,
            walletAddress=wallet.wallet_address,
        )
    except Exception as exc:
        raise map_service_error(exc) from exc


@router.get("/{agent_id}/analytics")
async def get_agent_analytics_summary(
    agent_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        return await AgentService(db).get_analytics_summary(agent_id)
    except Exception as exc:
        raise map_service_error(exc) from exc
