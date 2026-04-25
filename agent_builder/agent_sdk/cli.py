from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


TYPE_CHOICES = ("string", "integer", "number", "boolean")


@dataclass(slots=True)
class FieldSpec:
    name: str
    type_name: str
    description: str
    required: bool = True
    default: object | None = None
    enum_values: list[str] | None = None


@dataclass(slots=True)
class PriceSpec:
    amount: str
    currency: str
    price_type: str


@dataclass(slots=True)
class AgentScaffoldConfig:
    target_dir: Path
    agent_name: str
    agent_id: str
    agent_description: str
    agent_version: str
    capability_name: str
    capability_id: str
    capability_description: str
    capability_category: str
    requires_payment: bool
    price: PriceSpec | None
    input_fields: list[FieldSpec]
    output_fields: list[FieldSpec]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="create-agent",
        description="Create a new agent folder from an interactive terminal prompt.",
    )
    parser.add_argument(
        "destination",
        nargs="?",
        help="Optional new agent folder path. If omitted, you will be prompted.",
    )
    args = parser.parse_args()

    config = collect_config(args.destination)
    write_agent_files(config)

    print()
    print(f"Created agent scaffold in: {config.target_dir}")
    print("Next steps:")
    print(f"1. cd {config.target_dir}")
    print("2. python -m venv .venv")
    print("3. .venv\\Scripts\\Activate.ps1")
    print("4. pip install -r requirements.txt")
    print("5. Copy-Item .env.example .env")
    print("6. Edit app\\agent.py to replace the placeholder run logic")
    print("7. uvicorn app.main:app --reload")


def collect_config(destination: str | None) -> AgentScaffoldConfig:
    destination_prompt = destination or prompt_required("New agent folder name")
    target_dir = Path(destination_prompt).expanduser().resolve()
    if target_dir.exists() and any(target_dir.iterdir()):
        raise SystemExit(f"Target directory '{target_dir}' already exists and is not empty.")

    default_agent_name = humanize_name(target_dir.name)
    agent_name = prompt_required("Agent name", default=default_agent_name)
    agent_id = prompt_required("Agent ID", default=f"{slugify(agent_name)}_001")
    agent_description = prompt_required(
        "Agent description",
        default=f"{agent_name} description",
    )
    agent_version = prompt_required("Agent version", default="1.0.0")

    default_capability_name = f"{agent_name} Task"
    capability_name = prompt_required("Capability name", default=default_capability_name)
    capability_id = prompt_required("Capability ID", default=slugify(capability_name))
    capability_description = prompt_required(
        "Capability description",
        default=f"Run {capability_name.lower()}",
    )
    capability_category = prompt_required("Capability category", default="general")

    requires_payment = prompt_yes_no("Requires payment?", default=False)
    price: PriceSpec | None = None
    if requires_payment:
        amount = prompt_required("Price amount", default="1.00")
        currency = prompt_required("Price currency", default="USDC")
        price_type = prompt_required("Price type", default="FIXED")
        price = PriceSpec(amount=amount, currency=currency, price_type=price_type)

    print()
    print("Define the capability input fields.")
    input_fields = collect_fields(default_first_name="text", require_one=True)

    print()
    print("Define the capability output fields.")
    output_fields = collect_fields(default_first_name="result", require_one=True, output_mode=True)

    return AgentScaffoldConfig(
        target_dir=target_dir,
        agent_name=agent_name,
        agent_id=agent_id,
        agent_description=agent_description,
        agent_version=agent_version,
        capability_name=capability_name,
        capability_id=capability_id,
        capability_description=capability_description,
        capability_category=capability_category,
        requires_payment=requires_payment,
        price=price,
        input_fields=input_fields,
        output_fields=output_fields,
    )


def collect_fields(
    *,
    default_first_name: str,
    require_one: bool,
    output_mode: bool = False,
) -> list[FieldSpec]:
    fields: list[FieldSpec] = []
    counter = 0

    while True:
        counter += 1
        default_name = default_first_name if counter == 1 else f"field_{counter}"
        name = prompt_required("Field name", default=default_name)
        type_name = prompt_choice("Field type", TYPE_CHOICES, default="string")
        description = prompt_required(
            "Field description",
            default=name.replace("_", " ").capitalize(),
        )
        required = True if output_mode else prompt_yes_no("Required?", default=True)
        enum_values_raw = prompt_optional("Enum values (comma separated, optional)")
        enum_values = parse_enum_values(enum_values_raw)

        default_value: object | None = None
        if not required:
            if prompt_yes_no("Provide a default value?", default=False):
                default_value_raw = prompt_required("Default value")
                default_value = parse_value(default_value_raw, type_name)

        fields.append(
            FieldSpec(
                name=name,
                type_name=type_name,
                description=description,
                required=required,
                default=default_value,
                enum_values=enum_values,
            )
        )

        if not prompt_yes_no(
            "Add another field?",
            default=False if counter >= 1 else require_one,
        ):
            break

    return fields


def write_agent_files(config: AgentScaffoldConfig) -> None:
    config.target_dir.mkdir(parents=True, exist_ok=True)
    app_dir = config.target_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    files = {
        config.target_dir / ".gitignore": build_gitignore(),
        config.target_dir / ".env.example": build_env_example(),
        config.target_dir / "requirements.txt": build_requirements(config.target_dir),
        config.target_dir / "README.md": build_readme(config),
        app_dir / "__init__.py": '"""Application package for the generated agent."""\n',
        app_dir / "main.py": build_main_py(),
        app_dir / "agent.py": build_agent_py(config),
    }

    for path, content in files.items():
        path.write_text(content, encoding="utf-8")


def build_gitignore() -> str:
    return dedent(
        """\
        __pycache__/
        *.py[cod]
        .pytest_cache/
        .agent_sdk/
        .venv/
        .env
        venv/
        """
    )


def build_env_example() -> str:
    return dedent(
        """\
        HF_TOKEN=hf_your_token_here
        HF_MODEL=katanemo/Arch-Router-1.5B:hf-inference
        """
    )


def build_requirements(target_dir: Path) -> str:
    project_root = Path(__file__).resolve().parent.parent
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        editable_target = relative_path_for_requirements(target_dir, project_root)
        dependency_line = f"-e {editable_target}"
    else:
        version = importlib.metadata.version("agent-sdk")
        dependency_line = f"agent-sdk=={version}"

    return dedent(
        f"""\
        {dependency_line}
        python-dotenv>=1.0,<2.0
        uvicorn[standard]>=0.34,<1.0
        """
    )


def build_readme(config: AgentScaffoldConfig) -> str:
    return dedent(
        f"""\
        # {config.agent_name}

        Generated agent scaffold powered by the shared `agent_sdk`.

        ## Setup

        ```bash
        python -m venv .venv
        .venv\\Scripts\\activate
        pip install -r requirements.txt
        ```

        ## Run

        ```bash
        uvicorn app.main:app --reload
        ```

        ## Deploy

        ```bash
        deploy-agent
        ```

        The deploy command runs local preflight checks first and only proceeds if `/health`, `/status`, `/capabilities`, and the manifest format pass validation.

        ## Test

        ```bash
        curl -X POST http://127.0.0.1:8000/invoke/demo-session ^
          -H "Content-Type: application/json" ^
          -d "{build_example_request_json(config)}"
        ```

        Edit `app/agent.py` to replace the placeholder logic with your real implementation.
        """
    )


def build_main_py() -> str:
    return dedent(
        """\
        from dotenv import load_dotenv

        from agent_sdk import create_agent_app_from_logic
        from app.agent import GeneratedAgentLogic

        load_dotenv()

        app = create_agent_app_from_logic(
            GeneratedAgentLogic(),
            root_message="Generated agent API is running",
        )
        """
    )


def build_agent_py(config: AgentScaffoldConfig) -> str:
    input_model_name = f"{pascal_case(config.capability_id)}Input"
    output_model_name = f"{pascal_case(config.capability_id)}Output"
    imports = [
        "from __future__ import annotations",
        "",
        "from pydantic import BaseModel, Field",
        "",
        "from agent_sdk import BaseAgentLogic, CapabilityPrice, HandlerResult",
    ]

    if any(field.enum_values for field in [*config.input_fields, *config.output_fields]):
        imports.insert(2, "from typing import Literal")

    sections = [
        "\n".join(imports),
        build_model_code(input_model_name, config.input_fields),
        build_model_code(output_model_name, config.output_fields),
        build_logic_class(config, input_model_name, output_model_name),
    ]

    return "\n\n".join(sections) + "\n"


def build_model_code(model_name: str, fields: list[FieldSpec]) -> str:
    lines = [f"class {model_name}(BaseModel):"]
    for field in fields:
        annotation = python_annotation(field)
        default_expr = field_default_expression(field)
        lines.append(
            f"    {field.name}: {annotation} = Field({default_expr}, description={python_literal(field.description)})"
        )
    return "\n".join(lines)


def build_logic_class(
    config: AgentScaffoldConfig,
    input_model_name: str,
    output_model_name: str,
) -> str:
    class_lines = [
        "class GeneratedAgentLogic(BaseAgentLogic):",
        f"    agent_id = {python_literal(config.agent_id)}",
        f"    agent_name = {python_literal(config.agent_name)}",
        f"    agent_description = {python_literal(config.agent_description)}",
        f"    agent_version = {python_literal(config.agent_version)}",
        "",
        f"    capability_id = {python_literal(config.capability_id)}",
        f"    capability_name = {python_literal(config.capability_name)}",
        f"    capability_description = {python_literal(config.capability_description)}",
        f"    capability_category = {python_literal(config.capability_category)}",
        f"    capability_requires_payment = {python_bool(config.requires_payment)}",
    ]

    if config.price is None:
        class_lines.append("    capability_price = None")
    else:
        class_lines.extend(
            [
                "    capability_price = CapabilityPrice(",
                f"        amount={python_literal(config.price.amount)},",
                f"        currency={python_literal(config.price.currency)},",
                f"        type={python_literal(config.price.price_type)},",
                "    )",
            ]
        )

    class_lines.extend(
        [
            "    capability_estimated_execution_time_seconds = 30",
            "",
            f"    input_model = {input_model_name}",
            f"    output_model = {output_model_name}",
            "",
            f"    async def run(self, payload: {input_model_name}, invocation) -> HandlerResult:",
            "        # TODO: Replace this placeholder logic with your real implementation.",
            "        return HandlerResult(",
            f"            result={output_model_name}(",
        ]
    )

    for field in config.output_fields:
        class_lines.append(
            f"                {field.name}={placeholder_expression(field, config.input_fields)},"
        )

    class_lines.extend(
        [
            "            )",
            "        )",
        ]
    )

    return "\n".join(class_lines)


def python_annotation(field: FieldSpec) -> str:
    base_annotation = annotation_from_type(field.type_name)
    if field.enum_values:
        base_annotation = "Literal[" + ", ".join(python_literal(value) for value in field.enum_values) + "]"

    if not field.required and field.default is None:
        return f"{base_annotation} | None"
    return base_annotation


def field_default_expression(field: FieldSpec) -> str:
    if field.required:
        return "..."
    return python_literal(field.default)


def annotation_from_type(type_name: str) -> str:
    return {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
    }[type_name]


def placeholder_expression(field: FieldSpec, input_fields: list[FieldSpec]) -> str:
    if field.type_name == "string":
        if input_fields:
            first_input = input_fields[0].name
            return f'f"TODO: implement {field.name.replace("_", " ")} using {{payload.{first_input}}}"'
        return python_literal("TODO: implement this field")
    if field.type_name == "integer":
        return "0"
    if field.type_name == "number":
        return "0.0"
    if field.type_name == "boolean":
        return "False"
    return python_literal("TODO")


def build_example_request_json(config: AgentScaffoldConfig) -> str:
    payload = {
        "capabilityId": config.capability_id,
        "input": {field.name: example_value(field) for field in config.input_fields},
    }
    return json.dumps(payload).replace('"', '\\"')


def example_value(field: FieldSpec) -> object:
    if field.enum_values:
        return field.enum_values[0]
    if field.default is not None:
        return field.default
    if field.type_name == "string":
        return f"example {field.name}"
    if field.type_name == "integer":
        return 1
    if field.type_name == "number":
        return 1.0
    if field.type_name == "boolean":
        return True
    return "example"


def prompt_required(label: str, default: str | None = None) -> str:
    while True:
        prompt_label = f"{label}"
        if default:
            prompt_label += f" [{default}]"
        value = input(f"{prompt_label}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        print("A value is required.")


def prompt_optional(label: str, default: str | None = None) -> str | None:
    prompt_label = f"{label}"
    if default:
        prompt_label += f" [{default}]"
    value = input(f"{prompt_label}: ").strip()
    if value:
        return value
    return default


def prompt_yes_no(label: str, *, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        value = input(f"{label} [{suffix}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer yes or no.")


def prompt_choice(label: str, choices: tuple[str, ...], *, default: str) -> str:
    joined = "/".join(choices)
    while True:
        value = input(f"{label} [{default}] ({joined}): ").strip().lower()
        if not value:
            return default
        if value in choices:
            return value
        print(f"Choose one of: {joined}")


def parse_enum_values(raw_value: str | None) -> list[str] | None:
    if not raw_value:
        return None
    values = [value.strip() for value in raw_value.split(",") if value.strip()]
    return values or None


def parse_value(raw_value: str, type_name: str) -> object:
    if type_name == "string":
        return raw_value
    if type_name == "integer":
        return int(raw_value)
    if type_name == "number":
        return float(raw_value)
    if type_name == "boolean":
        normalized = raw_value.lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False
        raise SystemExit("Boolean defaults must be true or false.")
    return raw_value


def relative_path_for_requirements(target_dir: Path, project_root: Path) -> str:
    return Path(os.path.relpath(project_root, start=target_dir)).as_posix()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return slug.strip("_") or "generated_agent"


def pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in slugify(value).split("_"))


def humanize_name(value: str) -> str:
    return " ".join(part.capitalize() for part in slugify(value).split("_"))


def python_literal(value: object) -> str:
    return repr(value)


def python_bool(value: bool) -> str:
    return "True" if value else "False"


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        raise SystemExit(1)
