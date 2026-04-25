from __future__ import annotations

import importlib
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agent_sdk.models import AgentManifest, HealthResponse, StatusResponse

REQUIRED_ROUTE_PATHS = {
    "/health",
    "/capabilities",
    "/status",
    "/cancel",
    "/invoke/{session_id}",
}


@dataclass(slots=True)
class PreflightCheck:
    name: str
    passed: bool
    detail: str


@dataclass(slots=True)
class PreflightReport:
    checks: list[PreflightCheck]
    manifest: AgentManifest


class PreflightError(RuntimeError):
    """Raised when an agent does not pass local deployment checks."""


def validate_agent_directory(agent_dir: Path) -> PreflightReport:
    app = _load_app(agent_dir)
    route_paths = {route.path for route in app.routes}

    checks: list[PreflightCheck] = []
    missing_paths = sorted(REQUIRED_ROUTE_PATHS - route_paths)
    if missing_paths:
        raise PreflightError(
            "Required routes are missing: " + ", ".join(missing_paths)
        )
    checks.append(
        PreflightCheck(
            name="required_routes",
            passed=True,
            detail="All standard agent endpoints are registered.",
        )
    )

    with TestClient(app) as client:
        health_response = client.get("/health")
        if health_response.status_code != 200:
            raise PreflightError(
                f"/health returned {health_response.status_code} instead of 200."
            )
        health = HealthResponse.model_validate(health_response.json())
        if health.status != "ok":
            raise PreflightError("/health did not return status='ok'.")
        checks.append(
            PreflightCheck(
                name="health_endpoint",
                passed=True,
                detail="/health returned a valid liveness response.",
            )
        )

        capabilities_response = client.get("/capabilities")
        if capabilities_response.status_code != 200:
            raise PreflightError(
                f"/capabilities returned {capabilities_response.status_code} instead of 200."
            )
        manifest = AgentManifest.model_validate(capabilities_response.json())
        checks.append(
            PreflightCheck(
                name="capabilities_format",
                passed=True,
                detail="The capabilities response matches the approved manifest schema.",
            )
        )

        status_response = client.get("/status")
        if status_response.status_code != 200:
            raise PreflightError(
                f"/status returned {status_response.status_code} instead of 200."
            )
        StatusResponse.model_validate(status_response.json())
        checks.append(
            PreflightCheck(
                name="status_endpoint",
                passed=True,
                detail="/status returned a valid agent status payload.",
            )
        )

    return PreflightReport(checks=checks, manifest=manifest)


def _load_app(agent_dir: Path) -> FastAPI:
    main_file = agent_dir / "app" / "main.py"
    if not main_file.exists():
        raise PreflightError(f"Expected app entrypoint at '{main_file}'.")

    with _import_context(agent_dir):
        try:
            module = importlib.import_module("app.main")
        except Exception as exc:
            raise PreflightError(f"Could not import app.main: {exc}") from exc

    app = getattr(module, "app", None)
    if not isinstance(app, FastAPI):
        raise PreflightError("app.main must expose a FastAPI application named 'app'.")
    return app


@contextmanager
def _import_context(agent_dir: Path):
    previous_cwd = Path.cwd()
    previous_path = list(sys.path)
    modules_to_clear = [
        module_name for module_name in sys.modules if module_name == "app" or module_name.startswith("app.")
    ]

    try:
        os.chdir(agent_dir)
        sys.path.insert(0, str(agent_dir))
        importlib.invalidate_caches()
        for module_name in modules_to_clear:
            sys.modules.pop(module_name, None)
        yield
    finally:
        os.chdir(previous_cwd)
        sys.path[:] = previous_path
