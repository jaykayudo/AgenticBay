from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.services.health_client import AgentHealthClient, HealthCheckResult


class AgentValidationError(Exception):
    """Raised when a submitted service agent does not satisfy onboarding checks."""


@dataclass(frozen=True)
class AgentValidationResult:
    base_url: str
    test_session_id: str
    capabilities: dict[str, Any]
    invoke_response: Any
    health: HealthCheckResult  # included so marketplace can store version etc.


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


class AgentValidator:
    def __init__(self, *, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._health_client = AgentHealthClient()

    async def validate(self, base_url: str) -> AgentValidationResult:
        normalized_base_url = normalize_base_url(base_url)
        test_session_id = f"validation-{uuid.uuid4()}"

        # /health is checked first — if it fails, skip everything else
        health = await self._validate_health(normalized_base_url)
        capabilities = await self._validate_capabilities(normalized_base_url)
        invoke_response = await self._validate_invoke(normalized_base_url, test_session_id)

        return AgentValidationResult(
            base_url=normalized_base_url,
            test_session_id=test_session_id,
            capabilities=capabilities,
            invoke_response=invoke_response,
            health=health,
        )

    async def _validate_health(self, base_url: str) -> HealthCheckResult:
        result = await self._health_client.check(base_url)

        if not result.healthy:
            raise AgentValidationError(
                f"GET /health failed: {result.reason or result.status}. "
                "The agent must respond to GET /health within 3 seconds with "
                '{"status": "ok"|"degraded", "ready": true}.'
            )

        if not result.ready:
            raise AgentValidationError(
                "GET /health returned ready=false. "
                "The agent must report ready=true before it can be onboarded."
            )

        return result

    async def _validate_capabilities(self, base_url: str) -> dict[str, Any]:
        url = f"{base_url}/capabilities"
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise AgentValidationError(f"GET {url} timed out.") from exc
        except httpx.HTTPStatusError as exc:
            raise AgentValidationError(
                f"GET {url} returned HTTP {exc.response.status_code}."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentValidationError(f"GET {url} did not return valid JSON.") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("message"), str):
            raise AgentValidationError('GET /capabilities must return {"message": "<string>"}.')

        return payload

    async def _validate_invoke(self, base_url: str, test_session_id: str) -> Any:
        url = f"{base_url}/invoke/{test_session_id}"
        body = {
            "command": "validation_check",
            "arguments": {
                "message": "AgenticBay onboarding validation",
            },
        }

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds, follow_redirects=True
            ) as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException as exc:
            raise AgentValidationError(f"POST {url} timed out.") from exc
        except httpx.HTTPStatusError as exc:
            raise AgentValidationError(
                f"POST {url} returned HTTP {exc.response.status_code}."
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AgentValidationError(f"POST {url} did not return valid JSON.") from exc
