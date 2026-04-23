from __future__ import annotations

from typing import Final

import httpx
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import RegisteredAgent
from app.schemas.agent import (
    AgentManifest,
    AgentRegistrationRequest,
    RegisteredAgentRead,
)

CAPABILITIES_PATH: Final[str] = "/capabilities"


class AgentRegistryError(Exception):
    """Base exception for agent registration failures."""


class AgentManifestFetchError(AgentRegistryError):
    """Raised when a remote agent manifest cannot be fetched or validated."""


class AgentRegistrationConflictError(AgentRegistryError):
    """Raised when an agent conflicts with an existing registration."""


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


class AgentRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, payload: AgentRegistrationRequest) -> tuple[RegisteredAgentRead, bool]:
        base_url = normalize_base_url(str(payload.base_url))
        manifest = payload.manifest or await self.fetch_manifest(base_url)

        existing_by_agent_id = await self.db.scalar(
            select(RegisteredAgent).where(RegisteredAgent.external_agent_id == manifest.agent_id)
        )
        existing_by_base_url = await self.db.scalar(
            select(RegisteredAgent).where(RegisteredAgent.base_url == base_url)
        )

        if (
            existing_by_base_url is not None
            and existing_by_agent_id is not None
            and existing_by_base_url.id != existing_by_agent_id.id
        ):
            raise AgentRegistrationConflictError(
                "This base URL is already registered to a different agent."
            )
        if existing_by_base_url is not None and existing_by_agent_id is None:
            raise AgentRegistrationConflictError(
                "This base URL is already registered to a different agent."
            )

        record = existing_by_agent_id or existing_by_base_url
        created = record is None
        manifest_payload = manifest.model_dump(by_alias=True, mode="json")

        if record is None:
            record = RegisteredAgent(
                external_agent_id=manifest.agent_id,
                name=manifest.name,
                description=manifest.description,
                version=manifest.version,
                base_url=base_url,
                manifest=manifest_payload,
                is_active=True,
            )
            self.db.add(record)
        else:
            record.external_agent_id = manifest.agent_id
            record.name = manifest.name
            record.description = manifest.description
            record.version = manifest.version
            record.base_url = base_url
            record.manifest = manifest_payload
            record.is_active = True

        await self.db.flush()
        await self.db.refresh(record)

        return self.serialize(record), created

    async def fetch_manifest(self, base_url: str) -> AgentManifest:
        capabilities_url = f"{normalize_base_url(base_url)}{CAPABILITIES_PATH}"
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(capabilities_url)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AgentManifestFetchError(
                f"Could not fetch the agent manifest from {capabilities_url}: {exc}"
            ) from exc

        try:
            return AgentManifest.model_validate(response.json())
        except ValidationError as exc:
            raise AgentManifestFetchError(
                "The remote /capabilities response does not match the expected manifest schema."
            ) from exc

    def serialize(self, record: RegisteredAgent) -> RegisteredAgentRead:
        return RegisteredAgentRead(
            id=record.id,
            agent_id=record.external_agent_id,
            name=record.name,
            description=record.description,
            version=record.version,
            base_url=record.base_url,
            manifest=AgentManifest.model_validate(record.manifest),
            is_active=record.is_active,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
