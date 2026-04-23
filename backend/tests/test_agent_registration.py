import os
from datetime import datetime, timezone
from typing import Any, cast
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_bay_test"
os.environ["DATABASE_URL_SYNC"] = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.api.deps import get_session
from app.main import app
from app.schemas.agent import RegisteredAgentRead
from app.services.agent_registry import AgentManifestFetchError, AgentRegistryService

REMOTE_MANIFEST = {
    "agentId": "research_agent_001",
    "name": "Research Agent",
    "description": "Produces structured research reports.",
    "version": "1.0.0",
    "capabilities": [
        {
            "id": "research_topic",
            "name": "Research Topic",
            "description": "Research a topic in depth.",
            "category": "research",
            "requiresPayment": False,
            "parameters": [
                {
                    "name": "topic",
                    "type": "string",
                    "description": "Topic to research.",
                    "required": True,
                }
            ],
            "estimatedExecutionTimeSeconds": 30,
            "outputSchema": {"summary": "string"},
        }
    ],
}


async def fake_get_session() -> object:
    return object()


@pytest.fixture(autouse=True)
def override_dependencies() -> None:
    app.dependency_overrides[get_session] = fake_get_session
    yield
    app.dependency_overrides.clear()


def build_registered_agent() -> RegisteredAgentRead:
    now = datetime.now(datetime.UTC)
    return RegisteredAgentRead(
        id=uuid4(),
        agent_id=REMOTE_MANIFEST["agentId"],
        name=REMOTE_MANIFEST["name"],
        description=REMOTE_MANIFEST["description"],
        version=REMOTE_MANIFEST["version"],
        base_url="https://agent.example.com",
        manifest=REMOTE_MANIFEST,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def test_register_agent_returns_created_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_register(
        self: AgentRegistryService, payload: Any
    ) -> tuple[RegisteredAgentRead, bool]:
        assert payload.manifest is not None
        return build_registered_agent(), True

    monkeypatch.setattr(AgentRegistryService, "register", fake_register)

    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/register",
        json={"baseUrl": "https://agent.example.com", "manifest": REMOTE_MANIFEST},
    )

    assert response.status_code == 201
    assert response.json()["message"] == "Agent registered."
    assert response.json()["agent"]["agentId"] == REMOTE_MANIFEST["agentId"]


def test_register_agent_returns_updated_response(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_register(
        self: AgentRegistryService, payload: Any
    ) -> tuple[RegisteredAgentRead, bool]:
        assert payload.manifest is None
        return build_registered_agent(), False

    monkeypatch.setattr(AgentRegistryService, "register", fake_register)

    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/register",
        json={"baseUrl": "https://agent.example.com"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Agent registration updated."


def test_register_agent_returns_bad_gateway_for_manifest_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_register(
        self: AgentRegistryService, payload: Any
    ) -> tuple[RegisteredAgentRead, bool]:
        raise AgentManifestFetchError("manifest fetch failed")

    monkeypatch.setattr(AgentRegistryService, "register", fake_register)

    client = TestClient(app)
    response = client.post(
        "/api/v1/agents/register",
        json={"baseUrl": "https://agent.example.com"},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "manifest fetch failed"


@pytest.mark.asyncio
async def test_fetch_manifest_reads_capabilities_document(monkeypatch: pytest.MonkeyPatch) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        async def get(self, url: str) -> httpx.Response:
            request = httpx.Request("GET", url)
            return httpx.Response(200, json=REMOTE_MANIFEST, request=request)

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    service = AgentRegistryService(cast(Any, None))
    manifest = await service.fetch_manifest("https://agent.example.com/")

    assert manifest.agent_id == REMOTE_MANIFEST["agentId"]
    assert manifest.capabilities[0].id == "research_topic"


@pytest.mark.asyncio
async def test_fetch_manifest_rejects_invalid_remote_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MockAsyncClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def __aenter__(self) -> "MockAsyncClient":
            return self

        async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            return None

        async def get(self, url: str) -> httpx.Response:
            request = httpx.Request("GET", url)
            return httpx.Response(200, json={"invalid": True}, request=request)

    monkeypatch.setattr(httpx, "AsyncClient", MockAsyncClient)

    service = AgentRegistryService(cast(Any, None))

    with pytest.raises(AgentManifestFetchError):
        await service.fetch_manifest("https://agent.example.com")
