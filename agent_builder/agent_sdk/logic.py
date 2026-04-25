from __future__ import annotations

from enum import Enum
from typing import Any, get_args, get_origin

from pydantic import BaseModel
from pydantic.fields import PydanticUndefined

from agent_sdk.models import (
    AgentCapability,
    AgentInvocation,
    AgentManifest,
    CapabilityParameter,
    CapabilityPrice,
    HandlerResult,
)


def _field_type_name(annotation: Any) -> str:
    origin = get_origin(annotation)
    if origin is None:
        if isinstance(annotation, type):
            if issubclass(annotation, BaseModel):
                return "object"
            if issubclass(annotation, Enum):
                return "string"
            if issubclass(annotation, bool):
                return "boolean"
            if issubclass(annotation, int):
                return "integer"
            if issubclass(annotation, float):
                return "number"
            if issubclass(annotation, str):
                return "string"
            if issubclass(annotation, list):
                return "array"
            if issubclass(annotation, dict):
                return "object"
        return "string"

    if origin in (list, tuple, set):
        return "array"
    if origin is dict:
        return "object"
    if origin is bool:
        return "boolean"
    if origin is int:
        return "integer"
    if origin is float:
        return "number"
    return "string"


def _field_enum_values(annotation: Any) -> list[Any] | None:
    origin = get_origin(annotation)
    if origin is None and isinstance(annotation, type) and issubclass(annotation, Enum):
        return [member.value for member in annotation]

    if str(origin) == "typing.Literal":
        return list(get_args(annotation))

    return None


def _schema_type_name(schema: dict[str, Any]) -> str:
    if "type" in schema:
        return str(schema["type"])

    for option in schema.get("anyOf", []):
        option_type = option.get("type")
        if option_type and option_type != "null":
            return str(option_type)

    return "string"


def _output_schema_from_model(model: type[BaseModel] | None) -> dict[str, str]:
    if model is None:
        return {}

    schema = model.model_json_schema()
    properties = schema.get("properties", {})
    return {
        name: _schema_type_name(definition)
        for name, definition in properties.items()
    }


class BaseAgentLogic:
    agent_id: str
    agent_name: str
    agent_description: str
    agent_version: str = "1.0.0"

    capability_id: str
    capability_name: str
    capability_description: str
    capability_category: str = "general"
    capability_requires_payment: bool = False
    capability_price: CapabilityPrice | None = None
    capability_estimated_execution_time_seconds: int = 30

    input_model: type[BaseModel]
    output_model: type[BaseModel] | None = None

    def manifest(self) -> AgentManifest:
        parameters: list[CapabilityParameter] = []
        for name, field in self.input_model.model_fields.items():
            default = None
            if field.default is not PydanticUndefined:
                default = field.default

            parameters.append(
                CapabilityParameter(
                    name=name,
                    type=_field_type_name(field.annotation),
                    description=field.description or name.replace("_", " ").capitalize(),
                    required=field.is_required(),
                    default=default,
                    enum=_field_enum_values(field.annotation),
                )
            )

        capability = AgentCapability(
            id=self.capability_id,
            name=self.capability_name,
            description=self.capability_description,
            category=self.capability_category,
            requiresPayment=self.capability_requires_payment,
            price=self.capability_price,
            parameters=parameters,
            estimatedExecutionTimeSeconds=self.capability_estimated_execution_time_seconds,
            outputSchema=_output_schema_from_model(self.output_model),
        )
        return AgentManifest(
            agentId=self.agent_id,
            name=self.agent_name,
            description=self.agent_description,
            version=self.agent_version,
            capabilities=[capability],
        )

    def input_models(self) -> dict[str, type[BaseModel]]:
        return {self.capability_id: self.input_model}

    async def handler(self, invocation: AgentInvocation) -> HandlerResult:
        payload = self.input_model.model_validate(invocation.input)
        result = await self.run(payload, invocation)
        if isinstance(result, HandlerResult):
            return result
        return HandlerResult(result=result)

    async def run(
        self,
        payload: BaseModel,
        invocation: AgentInvocation,
    ) -> Any:
        raise NotImplementedError

