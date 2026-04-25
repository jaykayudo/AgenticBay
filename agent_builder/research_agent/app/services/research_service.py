import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from agent_sdk.huggingface import (
    HuggingFaceChatClient,
    HuggingFaceClientError,
)

REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "heading": {"type": "string"},
                    "content": {"type": "string"},
                    "keyPoints": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["heading", "content", "keyPoints"],
            },
        },
    },
    "required": ["title", "summary", "sections"],
}

SYSTEM_PROMPT = (
    "You are a careful research assistant. Return only valid JSON that matches the requested schema."
)


class ResearchDepth(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ResearchInput(BaseModel):
    topic: str = Field(..., min_length=1, description="The topic to research.")
    depth: ResearchDepth = Field(
        default=ResearchDepth.MEDIUM,
        description="Desired level of detail for the report.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional structured context for the task.",
    )


class ResearchSection(BaseModel):
    heading: str
    content: str
    keyPoints: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    title: str
    summary: str
    sections: list[ResearchSection]


@dataclass(slots=True)
class ResearchGeneration:
    provider: str
    model: str
    report: ResearchReport
    usage: dict[str, Any] | None = None


class ResearchServiceError(RuntimeError):
    """Raised when the research service cannot produce a report."""


class ResearchService:
    def __init__(self, client: HuggingFaceChatClient | None = None) -> None:
        self._client = client or HuggingFaceChatClient()

    async def generate_report(self, payload: ResearchInput) -> ResearchGeneration:
        prompt = self._build_prompt(payload)
        try:
            response = await self._client.generate_structured_json(
                prompt=prompt,
                schema=REPORT_SCHEMA,
                system_prompt=SYSTEM_PROMPT,
            )
        except HuggingFaceClientError as exc:
            raise ResearchServiceError(str(exc)) from exc

        try:
            report = ResearchReport.model_validate(response.payload)
        except Exception as exc:
            raise ResearchServiceError(
                "The AI provider returned JSON that does not match the research schema."
            ) from exc

        return ResearchGeneration(
            provider=response.provider,
            model=response.model,
            report=report,
            usage=response.usage,
        )

    @staticmethod
    def _build_prompt(payload: ResearchInput) -> str:
        depth_instructions = {
            ResearchDepth.LOW: "Provide a compact report with 3 short sections.",
            ResearchDepth.MEDIUM: "Provide a balanced report with 4 to 5 sections.",
            ResearchDepth.HIGH: "Provide a detailed report with 5 to 7 sections and richer key points.",
        }
        serialized_context = (
            json.dumps(payload.context, ensure_ascii=True) if payload.context else "{}"
        )
        return (
            "Generate a structured research report on the topic below.\n"
            "Use general model knowledge unless the supplied context says otherwise.\n"
            "Avoid fabricated citations, and mention uncertainty inside the prose when needed.\n"
            f"{depth_instructions[payload.depth]}\n"
            f"Topic: {payload.topic}\n"
            f"Supplemental context: {serialized_context}\n"
            "Return JSON with this shape:\n"
            "{"
            '"title": "string", '
            '"summary": "string", '
            '"sections": ['
            '{"heading": "string", "content": "string", "keyPoints": ["string"]}'
            "]"
            "}"
        )

