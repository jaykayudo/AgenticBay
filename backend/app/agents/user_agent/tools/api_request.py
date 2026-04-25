from __future__ import annotations

import logging
from typing import Any

import aiohttp

from app.agents.user_agent.tools.base import Tool

logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)


class ApiRequestTool(Tool):
    name = "api_request"
    description = (
        "Make an HTTP request to an external URL. "
        "Use this for fetching data needed to complete a task or calling utility endpoints. "
        "Do NOT use this for marketplace API calls — those go through send_orchestrator_message."
    )
    input_schema: dict[str, Any] = {
        "type": "object",
        "required": ["method", "url"],
        "properties": {
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"]},
            "url": {"type": "string"},
            "headers": {"type": "object"},
            "body": {"type": "object"},
        },
    }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        method = input["method"]
        url = input["url"]
        headers = input.get("headers", {})
        body = input.get("body")

        try:
            async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
                async with session.request(method, url, headers=headers, json=body) as response:
                    content_type = response.content_type or ""
                    if "json" in content_type:
                        body_data: Any = await response.json()
                    else:
                        body_data = await response.text()

                    return {"status": response.status, "body": body_data}
        except Exception as exc:
            logger.error("api_request failed: %s", exc)
            return {"status": 0, "error": str(exc)}
