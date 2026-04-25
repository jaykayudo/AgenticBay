"""
Shared test fixtures for the marketplace user agent.

Fakes:
  - FakeUserWS       — captures outbound messages to the frontend
  - FakeOrchestratorWS — captures outbound messages to the orchestrator
  - FakeMemory       — in-memory (no Redis) conversation history
  - FakeAgentLLM     — returns a scripted sequence of LLM responses
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from app.agents.user_agent.agent import MarketplaceUserAgent
from app.agents.user_agent.types import AutoPaySettings

# ── WebSocket fakes ──────────────────────────────────────────────────────────


class FakeUserWS:
    """Captures messages sent to the frontend."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send(self, payload: dict[str, Any]) -> None:
        self.messages.append(payload)

    async def close(self) -> None:
        pass

    def of_type(self, msg_type: str) -> list[dict[str, Any]]:
        return [m for m in self.messages if m.get("type") == msg_type]


class FakeOrchestratorWS:
    """Captures messages sent to the orchestrator."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def start_and_connect(self) -> None:
        pass

    async def send(self, payload: dict[str, Any]) -> None:
        self.sent.append(payload)

    async def close(self) -> None:
        pass


# ── Memory fake ───────────────────────────────────────────────────────────────


class FakeMemory:
    """In-memory conversation store — no Redis."""

    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []

    async def add_user_message(self, content: str) -> None:
        self._messages.append({"role": "user", "content": content})

    async def add_assistant_message(self, content: list[dict[str, Any]]) -> None:
        self._messages.append({"role": "assistant", "content": content})

    async def add_tool_result(self, tool_use_id: str, result: dict[str, Any]) -> None:
        self._messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(result),
                    }
                ],
            }
        )

    async def add_system_context(self, context: str) -> None:
        self._messages.append({"role": "user", "content": f"[SYSTEM CONTEXT] {context}"})

    async def get_messages_for_llm(self) -> list[dict[str, Any]]:
        return list(self._messages)

    async def clear(self) -> None:
        self._messages.clear()


# ── LLM fake ─────────────────────────────────────────────────────────────────


def _tool_use_block(name: str, input: dict[str, Any], tool_id: str = "tu_1") -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = input
    block.id = tool_id
    block.model_dump.return_value = {
        "type": "tool_use",
        "name": name,
        "id": tool_id,
        "input": input,
    }
    return block


def _text_block(text: str) -> MagicMock:
    block = MagicMock()
    block.type = "text"
    block.text = text
    block.model_dump.return_value = {"type": "text", "text": text}
    return block


def _llm_response(blocks: list[MagicMock], stop_reason: str = "tool_use") -> MagicMock:
    resp = MagicMock()
    resp.content = blocks
    resp.stop_reason = stop_reason
    return resp


class ScriptedLLM:
    """Returns a pre-programmed sequence of LLM responses."""

    def __init__(self, responses: list[MagicMock]) -> None:
        self._responses = list(responses)
        self._idx = 0

    async def call_with_tools(self, *, messages, tools, system, max_tokens=4096) -> MagicMock:
        if self._idx >= len(self._responses):
            # Safety fallback: return an empty end_turn so the loop exits cleanly
            return _llm_response([_text_block("")], stop_reason="end_turn")
        resp = self._responses[self._idx]
        self._idx += 1
        return resp


# ── Agent builder ─────────────────────────────────────────────────────────────


def build_agent(
    llm_responses: list[MagicMock],
    auto_pay: AutoPaySettings | None = None,
) -> tuple[MarketplaceUserAgent, FakeUserWS, FakeOrchestratorWS]:
    """Build a fully wired agent with fakes instead of real I/O."""
    agent = MarketplaceUserAgent(session_id="test-session", user_id="test-user")

    # Swap in fakes
    fake_user_ws = FakeUserWS()
    fake_orch_ws = FakeOrchestratorWS()

    agent.user_ws = fake_user_ws  # type: ignore[assignment]
    agent.memory = FakeMemory()  # type: ignore[assignment]
    agent.llm = ScriptedLLM(llm_responses)  # type: ignore[assignment]
    agent.orchestrator_ws = fake_orch_ws  # type: ignore[assignment]

    _auto_pay = auto_pay or AutoPaySettings(
        auto_pay_enabled=False,
        auto_pay_max_per_job=0,
        auto_pay_max_per_day=0,
    )

    # Patch the DB call used by payment_handler
    async def _fake_get_auto_pay() -> AutoPaySettings:
        return _auto_pay

    agent._get_auto_pay_settings = _fake_get_auto_pay  # type: ignore[method-assign]

    # Re-build tools so they reference the updated agent
    agent.tools = agent._build_tools()

    return agent, fake_user_ws, fake_orch_ws
