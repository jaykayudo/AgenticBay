from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class CapabilityPrice(APIModel):
    amount: str
    currency: str
    type: str


class CapabilityParameter(APIModel):
    name: str
    type: str
    description: str
    required: bool
    default: Any | None = None
    enum: list[Any] | None = None

    @model_validator(mode="after")
    def validate_parameter(self) -> CapabilityParameter:
        if self.enum is not None and self.default is not None and self.default not in self.enum:
            raise ValueError("Capability parameter default must be one of the enum values.")
        return self


class AgentCapability(APIModel):
    id: str
    name: str
    description: str
    category: str
    requires_payment: bool = Field(default=False, alias="requiresPayment")
    price: CapabilityPrice | None = None
    parameters: list[CapabilityParameter] = Field(default_factory=list)
    estimated_execution_time_seconds: int = Field(default=30, alias="estimatedExecutionTimeSeconds")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")

    @model_validator(mode="after")
    def validate_capability(self) -> AgentCapability:
        parameter_names = [parameter.name for parameter in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("Capability parameter names must be unique.")
        if self.requires_payment and self.price is None:
            raise ValueError("A paid capability must define a price.")
        if not self.requires_payment and self.price is not None:
            raise ValueError("An unpaid capability should not define a price.")
        if self.estimated_execution_time_seconds <= 0:
            raise ValueError("estimatedExecutionTimeSeconds must be greater than zero.")
        if not self.output_schema:
            raise ValueError("Each capability must declare a non-empty outputSchema.")
        return self


class AgentManifest(APIModel):
    agent_id: str = Field(alias="agentId")
    name: str
    description: str
    version: str
    capabilities: list[AgentCapability]

    @model_validator(mode="after")
    def validate_manifest(self) -> AgentManifest:
        if not self.capabilities:
            raise ValueError("Agent manifest must expose at least one capability.")
        capability_ids = [capability.id for capability in self.capabilities]
        if len(capability_ids) != len(set(capability_ids)):
            raise ValueError("Capability IDs must be unique within an agent manifest.")
        return self


class AgentRegistrationRequest(APIModel):
    base_url: AnyHttpUrl = Field(alias="baseUrl")
    manifest: AgentManifest | None = None


class RegisteredAgentRead(APIModel):
    id: UUID
    agent_id: str = Field(alias="agentId")
    name: str
    description: str
    version: str
    base_url: str = Field(alias="baseUrl")
    manifest: AgentManifest
    is_active: bool = Field(alias="isActive")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class AgentRegistrationResponse(APIModel):
    message: str
    agent: RegisteredAgentRead
