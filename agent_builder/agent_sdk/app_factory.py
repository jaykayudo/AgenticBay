from __future__ import annotations

from collections.abc import Mapping

from fastapi import Body, FastAPI, HTTPException, status
from pydantic import BaseModel

from agent_sdk.logic import BaseAgentLogic
from agent_sdk.models import (
    AgentManifest,
    CancelRequest,
    CancelResponse,
    HealthResponse,
    InvokeRequest,
    InvokeResponse,
    StatusResponse,
)
from agent_sdk.runtime import (
    AgentBusyError,
    AgentHandler,
    AgentRuntime,
    CapabilityNotFoundError,
    CapabilitySelectionError,
)


def create_agent_app(
    *,
    manifest: AgentManifest,
    handler: AgentHandler,
    input_models: Mapping[str, type[BaseModel]] | None = None,
    root_message: str | None = None,
) -> FastAPI:
    runtime = AgentRuntime(
        manifest=manifest,
        handler=handler,
        input_models=input_models,
    )
    app = FastAPI(
        title=f"{manifest.name} API",
        version=manifest.version,
    )

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {"message": root_message or f"{manifest.name} API is running"}

    @app.get("/health", response_model=HealthResponse, tags=["health"], summary="Heartbeat check")
    async def health_check() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.get(
        "/capabilities",
        response_model=AgentManifest,
        tags=["agent"],
        summary="Describe the agent contract",
    )
    async def get_capabilities() -> AgentManifest:
        return manifest

    @app.get("/status", response_model=StatusResponse, tags=["agent"], summary="Check agent status")
    async def get_status() -> StatusResponse:
        return runtime.get_status()

    @app.post(
        "/invoke/{session_id}",
        response_model=InvokeResponse,
        status_code=status.HTTP_202_ACCEPTED,
        tags=["agent"],
        summary="Submit work to the agent",
    )
    async def invoke_agent(session_id: str, payload: InvokeRequest) -> InvokeResponse:
        try:
            run = await runtime.invoke(session_id=session_id, payload=payload)
        except AgentBusyError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc
        except CapabilityNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except CapabilitySelectionError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        return InvokeResponse(
            message="Task accepted.",
            run=run,
        )

    @app.post("/cancel", response_model=CancelResponse, tags=["agent"], summary="Cancel the active run")
    async def cancel_run(payload: CancelRequest | None = Body(default=None)) -> CancelResponse:
        payload = payload or CancelRequest()

        try:
            run = await runtime.cancel(session_id=payload.session_id)
        except LookupError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        return CancelResponse(
            message="Active run cancelled.",
            run=run,
        )

    return app


def create_agent_app_from_logic(
    logic: BaseAgentLogic,
    *,
    root_message: str | None = None,
) -> FastAPI:
    return create_agent_app(
        manifest=logic.manifest(),
        handler=logic.handler,
        input_models=logic.input_models(),
        root_message=root_message,
    )
