from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import aiohttp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.agents import Agent, AgentAction, AgentHostingType, AgentStatus
from app.models.users import User
from app.services.agent_validator import AgentValidationResult, AgentValidator, normalize_base_url
from app.services.circle_client import CircleClient
from app.services.vector_service import VectorService


class AgentServiceError(Exception):
    """Base exception for owner-facing agent operations."""


class AgentNotFoundError(AgentServiceError):
    """Raised when an agent does not exist."""


class AgentOwnershipError(AgentServiceError):
    """Raised when a user tries to mutate another owner's agent."""


class AgentConflictError(AgentServiceError):
    """Raised when an agent slug or base URL conflicts with another listing."""


class AgentWalletProvisionError(AgentServiceError):
    """Raised when Circle wallet provisioning fails."""


class AgentImageUploadError(AgentServiceError):
    """Raised when profile image upload fails."""


@dataclass(frozen=True)
class AgentWallet:
    circle_wallet_id: str
    wallet_address: str


class ProfileImageStorage:
    """Small object-storage facade.

    Production deployments can replace this with S3/R2/GCS. For now, URL inputs are treated as
    already uploaded assets, while inline data is mapped to a deterministic CDN-style URL.
    """

    async def upload(
        self, *, agent_slug: str, image_url: str | None, image_data: str | None
    ) -> str | None:
        if image_url:
            return str(image_url)
        if not image_data:
            return None
        if not image_data.startswith("data:image/"):
            raise AgentImageUploadError("Profile image data must be a data:image/* payload.")
        cdn_base_url = "https://cdn.agenticbay.local/agents"
        return f"{cdn_base_url}/{agent_slug}/profile-image"


class AgentWalletService:
    def __init__(self, circle: CircleClient | None = None) -> None:
        self.circle = circle or CircleClient()

    async def create_wallet(self, *, agent_name: str) -> AgentWallet:
        try:
            wallet = await self.circle.create_developer_wallet(
                wallet_set_id=settings.CIRCLE_WALLET_SET_ID,
                blockchain=settings.BLOCKCHAIN,
                name=f"{agent_name} payout wallet",
            )
        except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as exc:
            raise AgentWalletProvisionError("Circle wallet could not be created.") from exc

        wallet_id = str(wallet.get("id") or "")
        wallet_address = str(wallet.get("address") or "")
        if not wallet_id or not wallet_address:
            raise AgentWalletProvisionError(
                "Circle wallet response did not include id and address."
            )

        return AgentWallet(circle_wallet_id=wallet_id, wallet_address=wallet_address)


def build_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"agent-{uuid.uuid4().hex[:8]}"


class AgentService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        validator: AgentValidator | None = None,
        wallet_service: AgentWalletService | None = None,
        vector_service: VectorService | None = None,
        image_storage: ProfileImageStorage | None = None,
    ) -> None:
        self.db = db
        self.validator = validator or AgentValidator()
        self.wallet_service = wallet_service or AgentWalletService()
        self.vector_service = vector_service or VectorService()
        self.image_storage = image_storage or ProfileImageStorage()

    async def list_owner_agents(self, owner: User) -> list[Agent]:
        result = await self.db.execute(
            select(Agent)
            .where(Agent.owner_id == owner.id)
            .options(selectinload(Agent.actions))
            .order_by(Agent.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_agent(self, agent_id: uuid.UUID) -> Agent:
        agent = await self._get_agent_with_actions(agent_id)
        if agent is None:
            raise AgentNotFoundError("Agent not found.")
        return agent

    async def validate_base_url(self, base_url: str) -> AgentValidationResult:
        return await self.validator.validate(base_url)

    async def submit_agent(self, owner: User, payload: Any) -> Agent:
        base_url = normalize_base_url(str(payload.base_url))
        slug = payload.slug or build_slug(payload.name)
        await self._ensure_unique_listing(slug=slug, base_url=base_url)

        validation = await self.validator.validate(base_url)
        wallet = await self.wallet_service.create_wallet(agent_name=payload.name)
        profile_image_url = await self.image_storage.upload(
            agent_slug=slug,
            image_url=payload.profile_image_url,
            image_data=payload.profile_image_data,
        )

        agent = Agent(
            owner_id=owner.id,
            name=payload.name,
            slug=slug,
            description=payload.description,
            profile_image_url=profile_image_url,
            hosting_type=AgentHostingType.EXTERNALLY_HOSTED,
            base_url=base_url,
            source_code_url=str(payload.source_code_url) if payload.source_code_url else None,
            status=AgentStatus.PENDING,
            categories=payload.categories,
            tags=payload.tags,
            circle_wallet_id=wallet.circle_wallet_id,
            wallet_address=wallet.wallet_address,
            capabilities_cache=validation.capabilities,
            pricing_summary=payload.pricing_summary,
        )

        self.db.add(agent)
        await self.db.flush()

        for action_payload in payload.actions:
            self.db.add(
                AgentAction(
                    agent_id=agent.id,
                    name=action_payload.name,
                    description=action_payload.description,
                    input_schema=action_payload.input_schema,
                    output_schema=action_payload.output_schema,
                    price=(
                        Decimal(str(action_payload.price_usdc))
                        if action_payload.price_usdc is not None
                        else None
                    ),
                    is_active=True,
                )
            )

        embedding_id = await self.vector_service.index_agent(self._vector_payload(agent))
        agent.embedding_id = embedding_id
        await self.db.flush()
        created_agent = await self._get_agent_with_actions(agent.id)
        if created_agent is None:
            raise AgentNotFoundError("Agent was created but could not be reloaded.")
        return created_agent

    async def update_agent(self, owner: User, agent_id: uuid.UUID, payload: Any) -> Agent:
        agent = await self.get_agent(agent_id)
        self._ensure_owner(agent, owner)

        updates = payload.model_dump(exclude_unset=True)
        if "base_url" in updates:
            agent.base_url = normalize_base_url(str(updates["base_url"]))
            validation = await self.validator.validate(agent.base_url)
            agent.capabilities_cache = validation.capabilities
        if "name" in updates:
            agent.name = updates["name"]
        if "description" in updates:
            agent.description = updates["description"]
        if "source_code_url" in updates:
            agent.source_code_url = (
                str(updates["source_code_url"]) if updates["source_code_url"] else None
            )
        if "categories" in updates:
            agent.categories = updates["categories"]
        if "tags" in updates:
            agent.tags = updates["tags"]
        if "pricing_summary" in updates:
            agent.pricing_summary = updates["pricing_summary"]
        if "profile_image_url" in updates or "profile_image_data" in updates:
            agent.profile_image_url = await self.image_storage.upload(
                agent_slug=agent.slug,
                image_url=updates.get("profile_image_url"),
                image_data=updates.get("profile_image_data"),
            )

        if {"name", "description", "categories", "tags", "pricing_summary"} & updates.keys():
            agent.embedding_id = await self.vector_service.index_agent(self._vector_payload(agent))

        await self.db.flush()
        updated_agent = await self._get_agent_with_actions(agent.id)
        if updated_agent is None:
            raise AgentNotFoundError("Agent was updated but could not be reloaded.")
        return updated_agent

    async def delete_agent(self, owner: User, agent_id: uuid.UUID) -> None:
        agent = await self.get_agent(agent_id)
        self._ensure_owner(agent, owner)
        await self.vector_service.remove_agent(str(agent.id))
        await self.db.delete(agent)
        await self.db.flush()

    async def set_status(self, owner: User, agent_id: uuid.UUID, status: AgentStatus) -> Agent:
        agent = await self.get_agent(agent_id)
        self._ensure_owner(agent, owner)
        if status not in {AgentStatus.ACTIVE, AgentStatus.PAUSED}:
            raise AgentServiceError("Only ACTIVE or PAUSED status updates are allowed.")
        agent.status = status
        await self.db.flush()
        updated_agent = await self._get_agent_with_actions(agent.id)
        if updated_agent is None:
            raise AgentNotFoundError("Agent was updated but could not be reloaded.")
        return updated_agent

    async def get_wallet(self, agent_id: uuid.UUID) -> AgentWallet:
        agent = await self.get_agent(agent_id)
        if not agent.circle_wallet_id or not agent.wallet_address:
            raise AgentNotFoundError("Agent wallet is not available.")
        return AgentWallet(
            circle_wallet_id=agent.circle_wallet_id, wallet_address=agent.wallet_address
        )

    async def get_analytics_summary(self, agent_id: uuid.UUID) -> dict[str, Any]:
        agent = await self.get_agent(agent_id)
        return {
            "agentId": str(agent.id),
            "agentName": agent.name,
            "status": agent.status.value,
            "totalJobs": agent.total_jobs,
            "successRate": float(agent.success_rate),
            "avgRating": float(agent.avg_rating),
            "totalEarned": float(agent.total_earned),
            "avgDurationSec": float(agent.avg_duration_sec)
            if agent.avg_duration_sec is not None
            else None,
        }

    async def _get_agent_with_actions(self, agent_id: uuid.UUID) -> Agent | None:
        result = await self.db.execute(
            select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.actions))
        )
        return result.scalar_one_or_none()

    async def _ensure_unique_listing(self, *, slug: str, base_url: str) -> None:
        result = await self.db.execute(
            select(Agent).where((Agent.slug == slug) | (Agent.base_url == base_url))
        )
        if result.scalar_one_or_none() is not None:
            raise AgentConflictError("An agent with this slug or base URL already exists.")

    def _ensure_owner(self, agent: Agent, owner: User) -> None:
        if agent.owner_id != owner.id:
            raise AgentOwnershipError("Only the agent owner can perform this action.")

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
