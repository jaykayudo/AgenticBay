from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable, Mapping

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from agent_sdk.models import (
    AgentInvocation,
    AgentManifest,
    AgentRun,
    HandlerResult,
    InvokeRequest,
    RunState,
    StatusResponse,
    utc_now,
)

AgentHandler = Callable[[AgentInvocation], Awaitable[HandlerResult] | HandlerResult]


class AgentBusyError(RuntimeError):
    """Raised when an invoke request arrives while the agent is already running."""


class CapabilityNotFoundError(LookupError):
    """Raised when a requested capability id is not exposed by the agent."""


class CapabilitySelectionError(ValueError):
    """Raised when the invoke request does not identify a capability clearly enough."""


class AgentRuntime:
    def __init__(
        self,
        *,
        manifest: AgentManifest,
        handler: AgentHandler,
        input_models: Mapping[str, type[BaseModel]] | None = None,
    ) -> None:
        self._manifest = manifest
        self._handler = handler
        self._input_models = dict(input_models or {})
        self._lock = asyncio.Lock()
        self._current_run: AgentRun | None = None
        self._current_task: asyncio.Task[None] | None = None

    def get_status(self) -> StatusResponse:
        is_running = self._is_running()
        run = self._copy_run(self._current_run)
        return StatusResponse(
            is_running=is_running,
            active_session_id=run.session_id if is_running and run else None,
            run=run,
        )

    async def invoke(self, session_id: str, payload: InvokeRequest) -> AgentRun:
        capability = self._resolve_capability(payload.capabilityId)
        normalized_input = self._normalize_input(capability.id, payload.input)

        async with self._lock:
            if self._is_running() and self._current_run is not None:
                raise AgentBusyError(
                    f"Agent is already running a task for session '{self._current_run.session_id}'."
                )

            now = utc_now()
            run = AgentRun(
                session_id=session_id,
                capabilityId=capability.id,
                input=normalized_input,
                state=RunState.RUNNING,
                submitted_at=now,
                updated_at=now,
            )
            invocation = AgentInvocation(
                session_id=session_id,
                capability=capability,
                input=normalized_input,
            )
            self._current_run = run
            self._current_task = asyncio.create_task(
                self._process_run(session_id=session_id, invocation=invocation)
            )
            return self._copy_run(run)

    async def cancel(self, session_id: str | None = None) -> AgentRun:
        async with self._lock:
            if not self._is_running() or self._current_run is None or self._current_task is None:
                raise LookupError("No active run to cancel.")

            if session_id is not None and session_id != self._current_run.session_id:
                raise ValueError(
                    f"Active run belongs to session '{self._current_run.session_id}', not '{session_id}'."
                )

            self._current_run.cancellation_requested = True
            self._current_run.updated_at = utc_now()
            task = self._current_task

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        return self._copy_run(self._current_run)

    async def _process_run(self, session_id: str, invocation: AgentInvocation) -> None:
        try:
            handler_result = self._handler(invocation)
            if inspect.isawaitable(handler_result):
                handler_result = await handler_result
            if not isinstance(handler_result, HandlerResult):
                handler_result = HandlerResult(result=handler_result)

            async with self._lock:
                if self._current_run is None or self._current_run.session_id != session_id:
                    return

                self._current_run.state = RunState.COMPLETED
                self._current_run.provider = handler_result.provider
                self._current_run.model = handler_result.model
                self._current_run.usage = jsonable_encoder(handler_result.usage)
                self._current_run.result = jsonable_encoder(handler_result.result)
                self._current_run.updated_at = utc_now()
                self._current_run.completed_at = self._current_run.updated_at
                self._current_task = None
        except asyncio.CancelledError:
            async with self._lock:
                if self._current_run is not None and self._current_run.session_id == session_id:
                    self._current_run.state = RunState.CANCELLED
                    self._current_run.updated_at = utc_now()
                    self._current_run.completed_at = self._current_run.updated_at
                    self._current_task = None
            raise
        except Exception as exc:
            async with self._lock:
                if self._current_run is not None and self._current_run.session_id == session_id:
                    self._current_run.state = RunState.FAILED
                    self._current_run.error = str(exc)
                    self._current_run.updated_at = utc_now()
                    self._current_run.completed_at = self._current_run.updated_at
                    self._current_task = None

    def _resolve_capability(self, capability_id: str | None):
        if capability_id is None:
            if len(self._manifest.capabilities) == 1:
                return self._manifest.capabilities[0]
            raise CapabilitySelectionError(
                "capabilityId is required because this agent exposes multiple capabilities."
            )

        capability = self._manifest.get_capability(capability_id)
        if capability is None:
            raise CapabilityNotFoundError(
                f"Capability '{capability_id}' is not supported by this agent."
            )
        return capability

    def _normalize_input(self, capability_id: str, payload: dict) -> dict:
        model = self._input_models.get(capability_id)
        if model is None:
            return jsonable_encoder(payload)

        validated = model.model_validate(payload)
        return jsonable_encoder(validated)

    def _is_running(self) -> bool:
        return self._current_task is not None and not self._current_task.done()

    @staticmethod
    def _copy_run(run: AgentRun | None) -> AgentRun | None:
        if run is None:
            return None
        return run.model_copy(deep=True)

