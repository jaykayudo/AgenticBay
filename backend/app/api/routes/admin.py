from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_session
from app.api.routes.agents import AgentRead, get_active_user, serialize_agent
from app.models.agents import Agent
from app.models.jobs import Job, JobStatus
from app.models.users import User, UserRole, UserStatus
from app.services.review_service import AgentReviewNotFoundError, ReviewService

router = APIRouter(prefix="/admin", tags=["admin"])


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class RejectAgentRequest(APIModel):
    reason: str = Field(min_length=1)


class UserStatusRequest(APIModel):
    status: UserStatus


class UserRead(APIModel):
    id: UUID
    email: str
    username: str | None
    display_name: str | None = Field(alias="displayName")
    role: UserRole
    status: UserStatus
    email_verified: bool = Field(alias="emailVerified")
    kyc_verified: bool = Field(alias="kycVerified")
    created_at: datetime = Field(alias="createdAt")


class AgentReviewDetail(APIModel):
    agent: AgentRead
    owner: UserRead
    source_code_url: str | None = Field(alias="sourceCodeUrl")
    review_notes: str | None = Field(alias="reviewNotes")
    proxy_contract_address: str | None = Field(alias="proxyContractAddress")


class JobAdminRead(APIModel):
    id: UUID
    session_id: UUID = Field(alias="sessionId")
    buyer_id: UUID = Field(alias="buyerId")
    agent_id: UUID = Field(alias="agentId")
    status: JobStatus
    amount_usdc: Decimal | None = Field(alias="amountUsdc")
    created_at: datetime = Field(alias="createdAt")
    started_at: datetime | None = Field(alias="startedAt")
    completed_at: datetime | None = Field(alias="completedAt")


class AdminStatsResponse(APIModel):
    users: int
    agents: int
    pending_agents: int = Field(alias="pendingAgents")
    jobs: int
    active_jobs: int = Field(alias="activeJobs")
    volume_usdc: float = Field(alias="volumeUsdc")


async def get_admin_user(current_user: User = Depends(get_active_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def serialize_user(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        username=user.username,
        displayName=user.display_name,
        role=user.role,
        status=user.status,
        emailVerified=user.email_verified,
        kycVerified=user.kyc_verified,
        createdAt=user.created_at,
    )


def serialize_review_detail(agent: Agent) -> AgentReviewDetail:
    return AgentReviewDetail(
        agent=serialize_agent(agent),
        owner=serialize_user(agent.owner),
        sourceCodeUrl=agent.source_code_url,
        reviewNotes=agent.review_notes,
        proxyContractAddress=agent.proxy_contract_address,
    )


def serialize_job(job: Job) -> JobAdminRead:
    amount = job.invoice.amount if job.invoice else None
    return JobAdminRead(
        id=job.id,
        sessionId=job.session_id,
        buyerId=job.buyer_id,
        agentId=job.agent_id,
        status=job.status,
        amountUsdc=amount,
        createdAt=job.created_at,
        startedAt=job.started_at,
        completedAt=job.completed_at,
    )


@router.get("/agents/pending", response_model=list[AgentRead])
async def list_pending_agents(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> list[AgentRead]:
    del admin
    agents = await ReviewService(db).pending_agents()
    return [serialize_agent(agent) for agent in agents]


@router.patch("/agents/{agent_id}/approve", response_model=AgentRead)
async def approve_agent(
    agent_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await ReviewService(db).approve_agent(agent_id, admin)
        return serialize_agent(agent)
    except AgentReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/agents/{agent_id}/reject", response_model=AgentRead)
async def reject_agent(
    agent_id: UUID,
    payload: RejectAgentRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> AgentRead:
    try:
        agent = await ReviewService(db).reject_agent(agent_id, admin, payload.reason)
        return serialize_agent(agent)
    except AgentReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/agents/{agent_id}/review", response_model=AgentReviewDetail)
async def get_agent_review_detail(
    agent_id: UUID,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> AgentReviewDetail:
    del admin
    try:
        agent = await ReviewService(db).review_detail(agent_id)
        return serialize_review_detail(agent)
    except AgentReviewNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/users", response_model=list[UserRead])
async def list_admin_users(
    role: UserRole | None = Query(default=None),
    status_filter: UserStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> list[UserRead]:
    del admin
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if status_filter is not None:
        stmt = stmt.where(User.status == status_filter)
    result = await db.execute(stmt)
    return [serialize_user(user) for user in result.scalars().all()]


@router.patch("/users/{user_id}/status", response_model=UserRead)
async def update_user_status(
    user_id: UUID,
    payload: UserStatusRequest,
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> UserRead:
    del admin
    if payload.status not in {UserStatus.SUSPENDED, UserStatus.BANNED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin status control only supports SUSPENDED or BANNED.",
        )
    try:
        user = await ReviewService(db).set_user_status(user_id, payload.status)
        return serialize_user(user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/jobs", response_model=list[JobAdminRead])
async def list_admin_jobs(
    status_filter: JobStatus | None = Query(default=None, alias="status"),
    buyer_id: UUID | None = Query(default=None, alias="buyerId"),
    agent_id: UUID | None = Query(default=None, alias="agentId"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> list[JobAdminRead]:
    del admin
    stmt = select(Job).options(selectinload(Job.invoice)).order_by(Job.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Job.status == status_filter)
    if buyer_id is not None:
        stmt = stmt.where(Job.buyer_id == buyer_id)
    if agent_id is not None:
        stmt = stmt.where(Job.agent_id == agent_id)
    result = await db.execute(stmt.offset(offset).limit(limit))
    return [serialize_job(job) for job in result.scalars().unique().all()]


@router.get("/stats", response_model=AdminStatsResponse)
async def get_admin_stats(
    admin: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_session),
) -> AdminStatsResponse:
    del admin
    stats = await ReviewService(db).admin_stats()
    return AdminStatsResponse.model_validate(stats)
