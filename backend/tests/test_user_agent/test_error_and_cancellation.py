"""
Error recovery and session cancellation tests.
"""

import pytest

from app.agents.user_agent.types import AgentState
from tests.test_user_agent.conftest import (
    _llm_response,
    _tool_use_block,
    build_agent,
)


@pytest.mark.asyncio
async def test_orchestrator_error_triggers_llm_turn() -> None:
    """An ERROR message from orchestrator injects context and triggers LLM."""
    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "user_feedback",
                    {"message": "An error occurred, retrying...", "type": "warning"},
                    "tu_1",
                ),
                _tool_use_block(
                    "send_orchestrator_message",
                    {"message_type": "SEARCH_AGENT", "data": {"message": "retry"}},
                    "tu_2",
                ),
            ]
        ),
    ]
    agent, fake_user_ws, fake_orch_ws = build_agent(responses)

    await agent.handle_orchestrator_message(
        {
            "type": "ERROR",
            "data": {"error_type": "search_error", "message": "Search service unavailable"},
        }
    )

    # LLM was called and reacted
    memory_msgs = await agent.memory.get_messages_for_llm()
    context_texts = [m["content"] for m in memory_msgs if isinstance(m.get("content"), str)]
    assert any("search_error" in t for t in context_texts)

    # User was informed
    warnings = [
        m for m in fake_user_ws.of_type("AGENT_MESSAGE") if m["data"]["message_type"] == "warning"
    ]
    assert len(warnings) >= 1


@pytest.mark.asyncio
async def test_error_recovery_close_session_on_unrecoverable() -> None:
    """LLM can choose to close the session on an unrecoverable error."""
    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "user_feedback",
                    {"message": "Unrecoverable error, closing.", "type": "warning"},
                    "tu_1",
                ),
                _tool_use_block(
                    "close_session",
                    {"final_result": "Error: service unavailable.", "success": False},
                    "tu_2",
                ),
            ]
        ),
    ]
    agent, fake_user_ws, fake_orch_ws = build_agent(responses)

    await agent.handle_orchestrator_message(
        {
            "type": "ERROR",
            "data": {"error_type": "connect_error", "message": "Service agent unreachable"},
        }
    )

    complete = fake_user_ws.of_type("SESSION_COMPLETE")
    assert len(complete) == 1
    assert complete[0]["data"]["success"] is False
    assert agent.state == AgentState.CLOSED


@pytest.mark.asyncio
async def test_cancel_session_closes_agent() -> None:
    """Calling agent.close() directly marks state CLOSED and clears memory."""
    responses = []
    agent, _, _ = build_agent(responses)

    await agent.close("Cancelled")

    assert agent.state == AgentState.CLOSED
    # Memory cleared
    msgs = await agent.memory.get_messages_for_llm()
    assert msgs == []


@pytest.mark.asyncio
async def test_unknown_tool_call_returns_error_result() -> None:
    """
    If LLM hallucinates a non-existent tool, the agent returns an error
    tool_result and continues without crashing.
    """
    from tests.test_user_agent.conftest import _llm_response, _text_block, _tool_use_block

    # Turn 1: calls a non-existent tool; turn 2: fallback text
    responses = [
        _llm_response(
            [
                _tool_use_block("nonexistent_tool", {"arg": "val"}, "tu_1"),
            ]
        ),
        _llm_response([_text_block("Okay, all done.")], stop_reason="end_turn"),
    ]

    agent, fake_user_ws, _ = build_agent(responses)
    await agent.run_llm_turn()

    # The error was captured in memory but the session kept running
    memory = await agent.memory.get_messages_for_llm()
    tool_results = [
        m
        for m in memory
        if isinstance(m.get("content"), list)
        and any(c.get("type") == "tool_result" for c in m["content"])
    ]
    assert len(tool_results) >= 1
    # The error string is embedded in the result
    result_content = str(tool_results[0]["content"])
    assert "Unknown tool" in result_content or "nonexistent" in result_content

    # User received the fallback text message
    msgs = fake_user_ws.of_type("AGENT_MESSAGE")
    assert any("done" in m["data"]["message"].lower() for m in msgs)


@pytest.mark.asyncio
async def test_user_prompt_tool_shows_modal() -> None:
    """user_prompt tool sends USER_PROMPT_MODAL to frontend."""
    responses = [
        _llm_response(
            [
                _tool_use_block(
                    "user_prompt",
                    {
                        "question": "Which format do you prefer?",
                        "input_type": "choice",
                        "options": ["PDF", "HTML", "Text"],
                    },
                    "tu_1",
                ),
            ]
        ),
    ]
    agent, fake_user_ws, _ = build_agent(responses)
    await agent.run_llm_turn()

    modals = fake_user_ws.of_type("USER_PROMPT_MODAL")
    assert len(modals) == 1
    assert modals[0]["data"]["question"] == "Which format do you prefer?"
    assert modals[0]["data"]["options"] == ["PDF", "HTML", "Text"]
    assert modals[0]["data"]["requires_response"] is True
    assert agent.state == AgentState.AWAITING_USER


@pytest.mark.asyncio
async def test_memory_persists_across_multiple_turns() -> None:
    """Messages accumulate in memory across multiple LLM turns."""
    from tests.test_user_agent.conftest import _text_block

    responses = [
        _llm_response([_text_block("Response from turn 1.")], stop_reason="end_turn"),
        _llm_response([_text_block("Response from turn 2.")], stop_reason="end_turn"),
    ]
    agent, _, _ = build_agent(responses)
    await agent.run_llm_turn()
    await agent.run_llm_turn()

    msgs = await agent.memory.get_messages_for_llm()
    # Both assistant turns should be stored
    assistant_turns = [m for m in msgs if m["role"] == "assistant"]
    assert len(assistant_turns) == 2
