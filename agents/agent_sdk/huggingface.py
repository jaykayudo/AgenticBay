from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

HUGGINGFACE_PROVIDER = "huggingface"
DEFAULT_HF_MODEL = "katanemo/Arch-Router-1.5B:hf-inference"
DEFAULT_HF_URL = "https://router.huggingface.co/v1/chat/completions"


@dataclass(slots=True)
class HuggingFaceStructuredResult:
    provider: str
    model: str
    payload: Any
    usage: dict[str, Any] | None = None


class HuggingFaceClientError(RuntimeError):
    """Raised when the Hugging Face client cannot produce a structured response."""


class HuggingFaceChatClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        model: str | None = None,
        base_url: str = DEFAULT_HF_URL,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self._token = token
        self._model = model
        self._base_url = base_url
        self._timeout = timeout or httpx.Timeout(90.0, connect=10.0)

    async def generate_structured_json(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        system_prompt: str,
        model: str | None = None,
        max_tokens: int = 1800,
        temperature: float = 0.2,
    ) -> HuggingFaceStructuredResult:
        token = self._token or os.getenv("HF_TOKEN")
        if not token:
            raise HuggingFaceClientError(
                "HF_TOKEN is required. Configure a Hugging Face token in your environment or .env file."
            )

        resolved_model = model or self._model or os.getenv("HF_MODEL", DEFAULT_HF_MODEL)
        payload = {
            "model": resolved_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_result",
                    "strict": True,
                    "schema": schema,
                },
            },
        }
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(self._base_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:300]
                raise HuggingFaceClientError(
                    f"Hugging Face request failed with status {exc.response.status_code}: {detail}"
                ) from exc
            except httpx.HTTPError as exc:
                raise HuggingFaceClientError(
                    "Could not reach Hugging Face Inference Providers."
                ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise HuggingFaceClientError(
                "Hugging Face returned an unexpected response shape."
            ) from exc

        return HuggingFaceStructuredResult(
            provider=HUGGINGFACE_PROVIDER,
            model=resolved_model,
            payload=self._parse_json_content(content),
            usage=data.get("usage"),
        )

    @staticmethod
    def _parse_json_content(content: Any) -> Any:
        if isinstance(content, (dict, list)):
            return content

        if not isinstance(content, str):
            raise HuggingFaceClientError(
                "Hugging Face returned content that could not be parsed as JSON."
            )

        normalized = content.strip()
        if normalized.startswith("```"):
            normalized = normalized.strip("`")
            if normalized.startswith("json"):
                normalized = normalized[4:].lstrip()

        try:
            return json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise HuggingFaceClientError(
                "Hugging Face returned invalid JSON."
            ) from exc

