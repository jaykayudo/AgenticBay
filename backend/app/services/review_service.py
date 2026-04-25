from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agents import Agent, AgentStatus
from app.models.invoices import Invoice, InvoiceStatus
from app.models.jobs import Job
from app.models.notifications import NotificationType
from app.models.users import User, UserStatus
from app.services.agent_service import AgentWalletService
from app.services.notification_service import NotificationService
from app.services.vector_service import VectorService


class ReviewServiceError(Exception):
    """Base review service error."""


class AgentReviewNotFoundError(ReviewServiceError):
    """Raised when the agent cannot be reviewed."""


@dataclass(frozen=True)
class ProxyDeployResult:
    proxy_contract_address: str
    status: str


class ProxyContractService:
    async def deploy_agent_proxy(self, agent: Agent) -> ProxyDeployResult:
        digest = hashlib.sha256(f"{agent.id}:{agent.slug}".encode()).hexdigest()[:40]
        return ProxyDeployResult(proxy_contract_address=f"0x{digest}", status="DEPLOYED")


class ReviewService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        wallet_service: AgentWalletService | None = None,
        vector_service: VectorService | None = None,
        proxy_service: ProxyContractService | None = None,
    ) -> None:
        self.db = db
        self.wallet_service = wallet_service or AgentWalletService()
        self.vector_service = vector_service or VectorService()
        self.proxy_service = proxy_service or ProxyContractService()

    async def pending_agents(self) -> list[Agent]:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.status == AgentStatus.PENDING)
            .options(selectinload(Agent.actions), selectinload(Agent.owner))
            .order_by(Agent.created_at.asc())
        )
        return list(result.scalars().unique().all())

    async def review_detail(self, agent_id: uuid.UUID) -> Agent:
        agent = await self._get_agent(agent_id)
        if agent is None:
            raise AgentReviewNotFoundError("Agent not found.")
        return agent

    async def approve_agent(self, agent_id: uuid.UUID, admin: User) -> Agent:
        del admin
        agent = await self.review_detail(agent_id)
        if not agent.circle_wallet_id or not agent.wallet_address:
            wallet = await self.wallet_service.create_wallet(agent_name=agent.name)
            agent.circle_wallet_id = wallet.circle_wallet_id
            agent.wallet_address = wallet.wallet_address

        deploy_result = await self.proxy_service.deploy_agent_proxy(agent)
        agent.proxy_contract_address = deploy_result.proxy_contract_address
        agent.embedding_id = await self.vector_service.index_agent(self._vector_payload(agent))
        agent.status = AgentStatus.ACTIVE
        agent.review_notes = "Approved by marketplace review."
        await self.db.flush()

        await NotificationService(self.db).create_notification(
            user_id=agent.owner_id,
            notification_type=NotificationType.REVIEW_RECEIVED,
            title="Agent approved",
            body=f"{agent.name} has been approved and is now live in the marketplace.",
            data={
                "agentId": str(agent.id),
                "status": agent.status.value,
                "proxyContractAddress": agent.proxy_contract_address,
            },
        )
        return await self.review_detail(agent.id)

    async def reject_agent(self, agent_id: uuid.UUID, admin: User, reason: str) -> Agent:
        del admin
        agent = await self.review_detail(agent_id)
        agent.status = AgentStatus.REJECTED
        agent.review_notes = reason
        await self.db.flush()

        await NotificationService(self.db).create_notification(
            user_id=agent.owner_id,
            notification_type=NotificationType.REVIEW_RECEIVED,
            title="Agent rejected",
            body=f"{agent.name} was rejected during marketplace review.",
            data={"agentId": str(agent.id), "status": agent.status.value, "reason": reason},
        )
        return await self.review_detail(agent.id)

    async def admin_stats(self) -> dict[str, Any]:
        users = await self.db.scalar(select(func.count()).select_from(User))
        agents = await self.db.scalar(select(func.count()).select_from(Agent))
        pending_agents = await self.db.scalar(
            select(func.count()).select_from(Agent).where(Agent.status == AgentStatus.PENDING)
        )
        jobs = await self.db.scalar(select(func.count()).select_from(Job))
        active_jobs = await self.db.scalar(
            select(func.count()).select_from(Job).where(Job.completed_at.is_(None))
        )
        volume = await self.db.scalar(
            select(func.coalesce(func.sum(Invoice.amount), 0)).where(
                Invoice.status.in_(
                    [
                        InvoiceStatus.PENDING_RELEASE,
                        InvoiceStatus.DISBURSING,
                        InvoiceStatus.DISBURSED,
                    ]
                )
            )
        )
        return {
            "users": int(users or 0),
            "agents": int(agents or 0),
            "pendingAgents": int(pending_agents or 0),
            "jobs": int(jobs or 0),
            "activeJobs": int(active_jobs or 0),
            "volumeUsdc": float(volume or 0),
        }

    async def set_user_status(self, user_id: uuid.UUID, status: UserStatus) -> User:
        user = await self.db.get(User, user_id)
        if user is None:
            raise LookupError("User not found.")
        user.status = status
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def _get_agent(self, agent_id: uuid.UUID) -> Agent | None:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .options(selectinload(Agent.actions), selectinload(Agent.owner))
        )
        return result.scalar_one_or_none()

    def _vector_payload(self, agent: Agent) -> dict[str, Any]:
        return {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "category": agent.categories[0] if agent.categories else "",
            "tags": agent.tags,
            "avg_rating": float(agent.avg_rating),
            "pricing_summary": agent.pricing_summary,
        }
