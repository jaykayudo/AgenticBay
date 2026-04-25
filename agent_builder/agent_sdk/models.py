from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunState(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CapabilityPrice(BaseModel):
    amount: str
    currency: str
    type: str


class CapabilityParameter(BaseModel):
    name: str
    type: str
    description: str
    required: bool
    default: Any | None = None
    enum: list[Any] | None = None

    @model_validator(mode="after")
    def validate_parameter(self) -> "CapabilityParameter":
        if self.enum is not None and self.default is not None and self.default not in self.enum:
            raise ValueError("Capability parameter default must be one of the enum values.")
        return self


class AgentCapability(BaseModel):
    id: str
    name: str
    description: str
    category: str
    requiresPayment: bool = False
    price: CapabilityPrice | None = None
    parameters: list[CapabilityParameter] = Field(default_factory=list)
    estimatedExecutionTimeSeconds: int = 30
    outputSchema: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_capability(self) -> "AgentCapability":
        parameter_names = [parameter.name for parameter in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("Capability parameter names must be unique.")
        if self.requiresPayment and self.price is None:
            raise ValueError("A paid capability must define a price.")
        if not self.requiresPayment and self.price is not None:
            raise ValueError("An unpaid capability should not define a price.")
        if self.estimatedExecutionTimeSeconds <= 0:
            raise ValueError("estimatedExecutionTimeSeconds must be greater than zero.")
        if not self.outputSchema:
            raise ValueError("Each capability must declare a non-empty outputSchema.")
        return self


class AgentManifest(BaseModel):
    agentId: str
    name: str
    description: str
    version: str
    capabilities: list[AgentCapability]

    @model_validator(mode="after")
    def validate_manifest(self) -> "AgentManifest":
        if not self.capabilities:
            raise ValueError("Agent manifest must expose at least one capability.")
        capability_ids = [capability.id for capability in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("Capability IDs must be unique within an agent manifest.")
        return self

    def get_capability(self, capability_id: str) -> AgentCapability | None:
        for capability in self.capabilities:
            if capability.id == capability_id:
                return capability
        return None


class InvokeRequest(BaseModel):
    capabilityId: str | None = Field(
        default=None,
        description="Capability to execute. Optional when the agent exposes exactly one capability.",
    )
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Capability-specific payload.",
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        if "input" in data:
            return data

        normalized = dict(data)
        capability_id = normalized.pop("capabilityId", None)
        if capability_id is None:
            capability_id = normalized.pop("capability_id", None)

        return {
            "capabilityId": capability_id,
            "input": normalized,
        }


class AgentInvocation(BaseModel):
    session_id: str
    capability: AgentCapability
    input: dict[str, Any]


class HandlerResult(BaseModel):
    result: Any
    provider: str | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None


class AgentRun(BaseModel):
    session_id: str
    capabilityId: str
    input: dict[str, Any]
    state: RunState
    submitted_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    provider: str | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None
    result: Any | None = None
    error: str | None = None
    cancellation_requested: bool = False


class InvokeResponse(BaseModel):
    message: str
    run: AgentRun


class StatusResponse(BaseModel):
    is_running: bool
    active_session_id: str | None = None
    run: AgentRun | None = None


class CancelRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        description="Optional session identifier to ensure the expected job is cancelled.",
    )


class CancelResponse(BaseModel):
    message: str
    run: AgentRun


class HealthResponse(BaseModel):
    status: str
    checked_at: datetime = Field(default_factory=utc_now)
