from __future__ import annotations

import argparse
import getpass
import json
import shutil
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from agent_sdk.cli import prompt_optional, prompt_required, prompt_yes_no, slugify
from agent_sdk.preflight import PreflightError, PreflightReport, validate_agent_directory

DEFAULT_CLOUD_RUN_REGION = "us-central1"
PROCFILE_CONTENT = "web: uvicorn app.main:app --host 0.0.0.0 --port $PORT\n"


@dataclass(slots=True)
class CloudRunDeploymentConfig:
    agent_dir: Path
    service_name: str
    project_id: str
    region: str
    public: bool
    env_vars: dict[str, str]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="deploy-agent",
        description="Validate and deploy an agent to Cloud Run, then print the live URL.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Agent folder to deploy. Defaults to the current directory.",
    )
    parser.add_argument("--project", help="Google Cloud project ID.")
    parser.add_argument("--region", help="Cloud Run region.")
    parser.add_argument("--service", help="Cloud Run service name.")
    parser.add_argument(
        "--private",
        action="store_true",
        help="Deploy without public internet access.",
    )
    args = parser.parse_args()

    agent_dir = Path(args.path).expanduser().resolve()
    report = validate_or_exit(agent_dir)
    config = collect_deployment_config(
        report=report,
        agent_dir=agent_dir,
        project_id=args.project,
        region=args.region,
        service_name=args.service,
        public=not args.private,
    )
    url = deploy_to_cloud_run(config)
    save_deployment_record(config, url)
    print()
    print(f"Deployment succeeded.")
    print(f"URL: {url}")


def validate_or_exit(agent_dir: Path) -> PreflightReport:
    print("Running preflight checks...")
    try:
        report = validate_agent_directory(agent_dir)
    except PreflightError as exc:
        raise SystemExit(f"Preflight failed: {exc}") from exc

    for check in report.checks:
        print(f"[pass] {check.name}: {check.detail}")

    print("Preflight checks passed. Deployment may continue.")
    return report


def collect_deployment_config(
    *,
    report: PreflightReport,
    agent_dir: Path,
    project_id: str | None,
    region: str | None,
    service_name: str | None,
    public: bool,
) -> CloudRunDeploymentConfig:
    ensure_gcloud_installed()

    default_project = project_id or get_gcloud_config_value("core/project")
    resolved_project = prompt_required("Google Cloud project ID", default=default_project)

    default_region = region or get_gcloud_config_value("run/region") or DEFAULT_CLOUD_RUN_REGION
    resolved_region = prompt_required("Cloud Run region", default=default_region)

    manifest = report.manifest
    default_service_name = service_name or slugify(manifest.agentId)
    resolved_service_name = prompt_required("Cloud Run service name", default=default_service_name)

    resolved_public = public
    if not public:
        print("Deploying as a private service.")
    else:
        resolved_public = prompt_yes_no(
            "Allow public internet access?",
            default=True,
        )

    env_vars = collect_runtime_env_vars(agent_dir)
    return CloudRunDeploymentConfig(
        agent_dir=agent_dir,
        service_name=resolved_service_name,
        project_id=resolved_project,
        region=resolved_region,
        public=resolved_public,
        env_vars=env_vars,
    )


def deploy_to_cloud_run(config: CloudRunDeploymentConfig) -> str:
    print("Deploying to Cloud Run...")
    command = [
        "gcloud",
        "run",
        "deploy",
        config.service_name,
        "--source",
        ".",
        "--project",
        config.project_id,
        "--region",
        config.region,
    ]

    if config.public:
        command.append("--no-invoker-iam-check")

    if config.env_vars:
        command.append(f"--set-env-vars={format_env_vars(config.env_vars)}")

    with temporary_procfile(config.agent_dir):
        run_subprocess(command, cwd=config.agent_dir)

    configure_service_access(config)
    url = describe_service_url(config)
    verify_remote_health(url)
    return url


def configure_service_access(config: CloudRunDeploymentConfig) -> None:
    access_flag = "--no-invoker-iam-check" if config.public else "--invoker-iam-check"
    run_subprocess(
        [
            "gcloud",
            "run",
            "services",
            "update",
            config.service_name,
            "--project",
            config.project_id,
            "--region",
            config.region,
            access_flag,
        ],
        cwd=config.agent_dir,
    )


def describe_service_url(config: CloudRunDeploymentConfig) -> str:
    output = run_subprocess(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            config.service_name,
            "--project",
            config.project_id,
            "--region",
            config.region,
            "--format=value(status.url)",
        ],
        cwd=config.agent_dir,
        capture_output=True,
    )
    url = output.strip()
    if not url:
        raise SystemExit("Cloud Run deployment completed, but no service URL was returned.")
    return url


def verify_remote_health(url: str) -> None:
    health_url = f"{url.rstrip('/')}/health"
    try:
        response = httpx.get(health_url, timeout=30.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SystemExit(
            f"Deployment completed, but the remote /health check failed: {exc}"
        ) from exc


def save_deployment_record(config: CloudRunDeploymentConfig, url: str) -> None:
    record_dir = config.agent_dir / ".agent_sdk"
    record_dir.mkdir(exist_ok=True)
    record = {
        "provider": "cloud-run",
        "service": config.service_name,
        "project": config.project_id,
        "region": config.region,
        "public": config.public,
        "url": url,
        "deployed_at": datetime.now(timezone.utc).isoformat(),
    }
    (record_dir / "deployment.json").write_text(
        json.dumps(record, indent=2),
        encoding="utf-8",
    )


def collect_runtime_env_vars(agent_dir: Path) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    dotenv_path = agent_dir / ".env"
    dotenv_values = load_dotenv_file(dotenv_path) if dotenv_path.exists() else {}

    if dotenv_values and prompt_yes_no("Use runtime env vars from .env?", default=True):
        env_vars.update(dotenv_values)

    if prompt_yes_no("Add or override runtime env vars manually?", default=False):
        while True:
            key = prompt_required("Env var name")
            if any(secret_hint in key.upper() for secret_hint in ("TOKEN", "KEY", "SECRET", "PASSWORD")):
                value = getpass.getpass(f"{key}: ")
            else:
                value = prompt_required(f"{key} value")
            env_vars[key] = value
            if not prompt_yes_no("Add another env var?", default=False):
                break

    return env_vars


def load_dotenv_file(dotenv_path: Path) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars


def ensure_gcloud_installed() -> None:
    if shutil.which("gcloud") is None:
        raise SystemExit("The gcloud CLI is required to deploy an agent to Cloud Run.")


def get_gcloud_config_value(property_name: str) -> str | None:
    try:
        value = run_subprocess(
            ["gcloud", "config", "get-value", property_name],
            capture_output=True,
        ).strip()
    except SystemExit:
        return None

    if not value or value == "(unset)":
        return None
    return value


def format_env_vars(env_vars: dict[str, str]) -> str:
    if not env_vars:
        return ""
    delimiter = "^@^"
    parts = [f"{key}={value}" for key, value in env_vars.items()]
    return delimiter + "@".join(parts)


def run_subprocess(
    command: list[str],
    *,
    cwd: Path | None = None,
    capture_output: bool = False,
) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            capture_output=capture_output,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Command not found: {command[0]}") from exc
    except subprocess.CalledProcessError as exc:
        if capture_output:
            detail = (exc.stderr or exc.stdout or "").strip()
            raise SystemExit(detail or f"Command failed: {' '.join(command)}") from exc
        raise SystemExit(f"Command failed: {' '.join(command)}") from exc

    if capture_output:
        return completed.stdout
    return ""


@contextmanager
def temporary_procfile(agent_dir: Path):
    procfile_path = agent_dir / "Procfile"
    created = False
    if not procfile_path.exists():
        procfile_path.write_text(PROCFILE_CONTENT, encoding="utf-8")
        created = True

    try:
        yield
    finally:
        if created and procfile_path.exists():
            procfile_path.unlink()
